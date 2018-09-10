import logging
import json
import re

from collections import namedtuple
from datetime import datetime

from hl7apy.core import Message
from hl7apy.parser import parse_message

from config import Config
from database import CursorFromPool
from msg_etl.utils import add_mllp_frame

logger = logging.getLogger('lis_server.mllpserver.c4800')


class C4800:
    """
    Class handles
    """
    def __init__(self, raw_msg):
        self.msg = parse_message(raw_msg)
        logger.debug('{}'.format(type(self.msg)))
        self.raw_results = self.msg.oul_r22_specimen
        logger.debug('{}'.format(type(self.raw_results)))
        self.instrument_info = None
        self.run_info = None

    # TODO error handling for NAKs
    def ack(self, resp_type='AA'):
        """
        Build ACK response for incoming message.
        :type resp_type: str
        :param resp_type: 'AA' for ACK, 'AR' for Reject, 'AE' for Application Error
        :rtype: HL7apy.core.Message
        :return: ACK ('AA') or NAK ('AE', 'AR') message
        """
        resp_types = ('AA', 'AR', 'AE')
        if resp_type not in resp_types:
            raise ValueError("Invalid ACK type. Expected one of: {}".format(resp_types))
        resp = Message('ACK', version='2.5.1')
        resp.msh.msh_3 = 'LIS'
        resp.msh.msh_4 = 'LIS Facility'
        resp.msh.msh_5 = self.msg.msh.msh_3
        resp.msh.msh_6 = Config.LABNAME
        resp.msh.msh_9 = 'ACK^R22^ACK'
        resp.msh.msh_10 = self.run_info.msg_guid
        resp.msh.msh_11 = 'P'
        resp.msh.msh_12 = '2.5.1'
        resp.msh.msh_18 = 'UNICODE UTF-8'
        resp.msh.msh_21 = 'LAB-29^IHE'
        resp.add_segment('MSA')
        resp.msa.msa_1 = resp_type
        resp.msa.msa_2 = self.run_info.msg_guid
        if resp_type != 'AA':
            pass
        end_resp = add_mllp_frame(
            resp.to_er7()
        )
        assert isinstance(end_resp, bytes)
        return end_resp

    def get_instrument_info(self):
        logger.info('Getting message instrument info...')
        instrument_info = namedtuple('Instrument', 'id model sn sw_version')
        model = self.msg.oul_r22_specimen[0].oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[0].obx.obx_18.ei_1.value
        sn = self.msg.msh.msh_3.msh_3_2.value
        sw = self.msg.msh.msh_3.msh_3_1.value
        pattern = '.*(\d\.\d\.\d\.\d{4})$'
        match = re.search(pattern, sw)
        sw_version = match.group(1)
        with CursorFromPool() as cur:
            cur.execute("""
            SELECT id, model, sn, sw_version FROM instruments
            WHERE model = %s AND sn = %s AND sw_version = %s;
            """, (model, sn, sw_version))
            result = cur.fetchone()
        if result is None:
            with CursorFromPool() as cur:
                cur.execute("""
                INSERT INTO instruments (model, sn, sw_version)
                VALUES (%s, %s, %s)
                RETURNING id, model, sn, sw_version;
                """, (model, sn, sw_version))
                update_result = cur.fetchone()
            self.instrument_info = instrument_info(*update_result)
        else:
            self.instrument_info = instrument_info(*result)
            logger.debug('Message instrument_info: {}'.format(self.instrument_info))

    def save_run_info(self):
        logger.info('Getting message run info...')
        run_info = namedtuple('Run', 'id instrument_id msg_ts msg_guid')
        msg_ts = datetime.strptime(self.msg.msh.msh_7.value, '%Y%m%d%H%M%S%z')
        msg_guid = self.msg.msh.msh_10.value
        with CursorFromPool() as cur:
            cur.execute("""
            INSERT INTO runs (instrument_id, msg_ts, msg_guid)
            VALUES (%s, %s, %s)
            RETURNING id, instrument_id, msg_ts, msg_guid;
            """, (self.instrument_info.id, msg_ts, msg_guid))
            result = cur.fetchone()
        self.run_info = run_info(*result)

    def get_assay_info(self):
        """
        Parses assay from HL7 message and queries assays table for relevant information.
        :return: namedtuple of assay information (id, instrument_id, lis_code, name)
        """
        logger.debug('Getting sample assay info...')
        assay = namedtuple('Assay', 'id instrument_id lis_code assay_name')
        lis_code = self.msg.oul_r22_specimen[0].oul_r22_order[0].obr.obr_4.obr_4_1.value
        with CursorFromPool() as cur:
            cur.execute("""
            SELECT * FROM assays WHERE instrument_id = %s AND lis_code =%s;
            """, (self.instrument_info.id, lis_code))
            result = cur.fetchone()
        if result is None:
            with CursorFromPool() as cur:
                cur.execute("""
                INSERT INTO assays (instrument_id, lis_code, assay_name)
                VALUES (%s, %s, %s)
                RETURNING id, instrument_id, lis_code, assay_name;
                """, (self.instrument_info.id, lis_code, 'temp'))
                update_result = cur.fetchone()
            return assay(*update_result)
        return assay(*result)

    @staticmethod
    def parse_cntrl_ct(ct):
        """
        Parses all channels/ids and numerical results for each channel.
        :param ct: raw ct information from HL7 message
        :rtype: JSON
        :return: channel name/id with numerical ct result in JSON
        """
        logger.debug('Parsing control ct values from message.')
        result = {}
        cts = ct.split(';')
        for x in cts:
            channel, ct = x.split(',')
            result[channel] = float(ct)
        return json.dumps(result)
    
    @staticmethod
    def process_result(x):
        if x[-5:].lower() == 'cp/ml':
            return x[:8]
        return x

    def _parse_result(self, elem):
        """
        Parses individual result information from a OUL_R22_SPECIMEN Group. One group will be present for all
        results in the HL7 message.
        This method should be called in a list comprehension to generate a tuple of values per result to be used to
        insert into database.
        :return:`Result` namedtuple
        """
        logger.debug('Parsing sample level results data from message...')
        results = namedtuple('Result', 'run_id assay_id sample_role sample_type sample_id result units result_status '
                                       'username flags cntrl_cts comments dwp_id mwp_id mwp_position start_ts end_ts')
        sample_role = elem.spm.spm_11.spm_11_1.value
        if sample_role == 'P':
            sample_type = elem.spm.spm_4.spm_4_1.value
        else:
            sample_type = elem.oul_r22_container[0].inv.inv_1.inv_1_1.value
        sample_id = elem.spm.spm_2.eip_1.ei_1.to_er7()
        # TODO implement parsing results (log10 numeric, TND, <LOD
        raw_result = elem.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[1].obx.obx_5.value
        result = self.process_result(raw_result)
        units = elem.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[1].obx.obx_6.obx_6_1.value
        result_status = elem.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[1].obx.obx_11.value
        username = elem.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[1].obx.obx_16.value
        flags_raw = elem.oul_r22_order[1].nte.nte_3.value
        flags_raw = flags_raw[2:].split(',')
        if flags_raw[0] == 'NONE' and len(flags_raw) == 1:
            flags = [""]
        else:
            flags = flags_raw
        if sample_role == 'Q' and sample_type != 'NEGCONTROL':
            cts_raw = elem.oul_r22_order[1].nte[1].nte_3.value
            cntrl_cts = C4800.parse_cntrl_ct(cts_raw)
        else:
            cntrl_cts = json.dumps({"":""})
        if sample_role == 'P':
            comments = elem.oul_r22_order[1].nte[2].nte_3.value
        else:
            comments = ''
        dwp_id = elem.oul_r22_container[2].inv.inv_5.inv_5_1.value
        mwp_id = elem.oul_r22_container[1].inv.inv_5.inv_5_1.value
        mwp_position = elem.oul_r22_container[1].inv.inv_6.inv_6_1.value
        start_ts = datetime.strptime(elem.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[0]
                                     .obx.obx_5.obx_5_1.value,
                                     '%Y%m%d%H%M%S')
        end_ts = datetime.strptime(elem.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[0]
                                   .obx.obx_5.obx_5_2.value,
                                   '%Y%m%d%H%M%S')
        return results(self.run_info.id, self.get_assay_info().id, sample_role, sample_type, sample_id, result, units,
                       result_status, username, flags, cntrl_cts, comments, dwp_id, mwp_id, mwp_position, start_ts,
                       end_ts)

    def _parse_results(self):
        logger.debug('Returning results parser generator...')
        for result in self.raw_results:
            yield C4800._parse_result(self, result)

    def save_results(self):
        """
        Inserts results into database
        """
        with CursorFromPool() as cur:
            for i, result in enumerate(self._parse_results(), start=1):
                logger.info('Inserting run {} - sample {} into results table...'.format(result.run_id, i))
                cur.execute("""
                    INSERT INTO results (run_id, assay_id, sample_role, sample_type, sample_id, result, units,
                      result_status, username, flags, cntrl_cts, comments, dwp_id, mwp_id, mwp_position, start_ts,
                      end_ts)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, result)
