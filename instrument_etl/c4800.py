import re

from collections import namedtuple
from datetime import datetime

from hl7apy.core import Message
from hl7apy.parser import parse_message

from config import Config
from database import CursorFromPool
from .utils import add_mllp_frame


class C4800Message:
    def __init__(self, msg):
        self.msg = parse_message(msg)
        self.msg_ts = datetime.strptime(self.msg.msh.msh_7.value, '%Y%m%d%H%M%S%z')
        self.msg_guid = self.msg.msh.msh_10.value
        self.instrument_id = None
        self.run_id = None

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
        resp.msh.msh_10 = self.msg.msh.msh_10
        resp.msh.msh_11 = 'P'
        resp.msh.msh_18 = 'UNICODE UTF-8'
        resp.msh.msh_21 = 'LAB-29^IHE'
        resp.add_segment('MSA')
        resp.msa.msa_1 = resp_type
        resp.msa.msa_2 = self.msg.msh.msh_10
        if resp_type != 'AA':
            pass
        end_resp = add_mllp_frame(
            resp.to_er7()
        )
        assert isinstance(end_resp, bytes)
        return end_resp

    def save_instrument_info(self):
        """
        Parses instrument information from HL7 message, and inserts into database if unique. Returns message's
        instrument information even if instrument data isn't inserted into database.
        """
        model = self.msg.oul_r22_specimen[0].oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[0].obx.obx_18.ei_1.value
        sn = self.msg.msh.msh_3.msh_3_2.value
        sw = self.msg.msh.msh_3.msh_3_1.value
        pattern = '.*(\d\.\d\.\d\.\d{4})$'
        match = re.search(pattern, sw)
        sw_version = match.group(1)
        instrument_info = (model, sn, sw_version)
        with CursorFromPool() as cur:
            cur.execute("""
            INSERT INTO instruments (model, sn, sw_version)
            VALUES (%s, %s, %s)
            ON CONFLICT ON CONSTRAINT inst_unique
            DO UPDATE SET status = 'return hack'
            RETURNING id;
            """, instrument_info)
            instrument_id = cur.fetchone()[0]
        self.instrument_id = instrument_id

    def save_run_info(self):
        """
        Parses run information from HL7 message, and inserts into database if message guid is unique. Returns message's
        run id even if data isn't inserted into database.
        """
        with CursorFromPool() as cur:
            cur.execute("""
            INSERT INTO runs (instrument_id, msg_ts, msg_guid)
            SELECT instrument_id, assayId, %s, %s FROM assay
            RETURNING id, assay_id;
            """, (self.instrument_id, self.msg_ts, self.msg_guid))
            run_id = cur.fetchone()[0]
        self.run_id = run_id

    def get_assay_info(self):
        """
        Parses assay from HL7 message and queries assays table for relevant information.
        :return: namedtuple of assay information (id, instrument_id, list_code, name)
        """
        assay = namedtuple('Assay', 'id instrument_id lis_code name')
        lis_code = self.msg.oul_r22_specimen[0].oul_r22_order[0].obr.obr_4.obr_4_1.value
        with CursorFromPool() as cur:
            cur.execute("""
            SELECT * FROM assays WHERE instrument_id = %s AND lis_code =%s;
            """, (self.instrument_id, lis_code))
            result = cur.fetchone()
        return assay(*result)

    # TODO add Control Ct message parsing
    @staticmethod
    def parse_result(spm, run_id, assay_id):
        """
        Parses individual result information from a OUL_R22_SPECIMEN Group. One group will be present for all
        results in the HL7 message.
        This method should be called in a list comprehension to generate a tuple of values per result to be used to
        insert into database.
        :param spm: HL7apy.core.OUL_R22_SPECIMEN from C4800Message
        :type run_id: int
        :param run_id: Run ID for message
        :type assay_id: int
        :param assay_id: Assay ID for result
        :return: tuple of result information values to be inserted into database
        """
        results = namedtuple('Result', 'run_id assay_id sample_role sample_type sample_id result units result_status '
                                       'username flags cntrl_cts comments dwp_id mwp_id mwp_position start_ts end_ts')
        sample_role = spm.spm.spm_11.spm_11_1.value
        if sample_role == 'P':
            sample_type = spm.spm.spm_4.spm_4_1.value
        else:
            sample_type = spm.oul_r22_container[0].inv.inv_1.inv_1_1.value
        sample_id = spm.spm.spm_2.to_er7()
        result = int(float(spm.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[1].obx.obx_5.value[:8]))
        units = spm.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[1].obx.obx_6.obx_6_1.value
        result_status = spm.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[1].obx.obx_11.value
        username = spm.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[1].obx.obx_16.value
        flags_raw = spm.oul_r22_order[1].nte.nte_3.value
        flags_raw = flags_raw[2:].split(',')
        if flags_raw[0] == 'NONE' and len(flags_raw) == 1:
            flags = None
        else:
            flags = flags_raw
        if sample_role == 'Q':
            cntrl_cts = '{"test": "todo"}'
        else:
            cntrl_cts = None
        if sample_role == 'P':
            comments = spm.oul_r22_order[1].nte[2].nte_3.value
        else:
            comments = None
        dwp_id = spm.oul_r22_container[2].inv.inv_5.inv_5_1.value
        mwp_id = spm.oul_r22_container[1].inv.inv_5.inv_5_1.value
        mwp_position = spm.oul_r22_container[1].inv.inv_6.inv_6_1.value
        start_ts = datetime.strptime(spm.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[0].obx.obx_5.obx_5_1.value,
                                     '%Y%m%d%H%M%S')
        end_ts = datetime.strptime(spm.oul_r22_order[0].oul_r22_obxtcdsidnte_suppgrp[0].obx.obx_5.obx_5_2.value,
                                   '%Y%m%d%H%M%S')
        return results(run_id, assay_id, sample_role, sample_type, sample_id, result, units, result_status, username,
                       flags,
                       cntrl_cts, comments, dwp_id, mwp_id, mwp_position, start_ts, end_ts)

    @staticmethod
    def save_results(results):
        """
        Inserts results into database
        :param results: list of results generated by parse_results()
        :return: None
        """
        with CursorFromPool() as cur:
            for result in results:
                cur.execute("""
                    INSERT INTO results (run_id, assay_id, sample_role, sample_type, sample_id, result, units,
                      result_status, username, flags, cntrl_cts, comments, dwp_id, mwp_id, mwp_position, start_ts,
                      end_ts)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, result)
