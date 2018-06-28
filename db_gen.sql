CREATE TABLE IF NOT EXISTS instruments
(
  id         SERIAL NOT NULL
    CONSTRAINT instruments_pkey
    PRIMARY KEY,
  model      VARCHAR(40),
  sn         VARCHAR(40),
  sw_version VARCHAR(50),
  CONSTRAINT inst_unique
  UNIQUE (model, sn, sw_version)
);

CREATE TABLE IF NOT EXISTS assays
(
  id            SERIAL      NOT NULL
    CONSTRAINT assays_pkey
    PRIMARY KEY,
  instrument_id INTEGER     NOT NULL
    CONSTRAINT assays_instrument_id_fkey
    REFERENCES instruments,
  lis_code      VARCHAR(10) NOT NULL,
  assay_name    VARCHAR(40) NOT NULL,
  num_channels  INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS runs
(
  id            SERIAL                                 NOT NULL
    CONSTRAINT runs_pkey
    PRIMARY KEY,
  instrument_id INTEGER                                NOT NULL
    CONSTRAINT runs_instrument_id_fkey
    REFERENCES instruments,
  msg_ts        TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
  msg_guid      UUID                                   NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS runs_msg_guid_uindex
  ON runs (msg_guid);

CREATE TABLE IF NOT EXISTS results
(
  id            SERIAL      NOT NULL
    CONSTRAINT results_pkey
    PRIMARY KEY,
  run_id        INTEGER     NOT NULL
    CONSTRAINT results_run_id_fkey
    REFERENCES runs,
  assay_id      INTEGER     NOT NULL
    CONSTRAINT results_assay_id_fkey
    REFERENCES assays,
  sample_role   VARCHAR(1)  NOT NULL,
  sample_type   VARCHAR(10) NOT NULL,
  sample_id     VARCHAR(40) NOT NULL,
  result        VARCHAR(50) NOT NULL,
  units         VARCHAR(10) NOT NULL,
  result_status VARCHAR(1)  NOT NULL,
  username      VARCHAR(20) NOT NULL,
  flags         TEXT [],
  cntrl_cts     JSONB,
  comments      VARCHAR(255),
  dwp_id        VARCHAR(20) NOT NULL,
  mwp_id        VARCHAR(20) NOT NULL,
  mwp_position  VARCHAR(3)  NOT NULL,
  start_ts      TIMESTAMP   NOT NULL,
  end_ts        TIMESTAMP   NOT NULL,
  CONSTRAINT cntrl_cts
  CHECK ((((sample_role) :: TEXT = 'P' :: TEXT) AND (cntrl_cts IS NULL)) OR
         (((sample_role) :: TEXT = 'Q' :: TEXT) AND (cntrl_cts IS NOT NULL)))
);

-- missing source code for uuid_nil
;

-- missing source code for uuid_ns_dns
;

-- missing source code for uuid_ns_url
;

-- missing source code for uuid_ns_oid
;

-- missing source code for uuid_ns_x500
;

-- missing source code for uuid_generate_v1
;

-- missing source code for uuid_generate_v1mc
;

-- missing source code for uuid_generate_v3
;

-- missing source code for uuid_generate_v4
;

-- missing source code for uuid_generate_v5
;

CREATE FUNCTION results_file(runid INTEGER)
  RETURNS TABLE(assay CHARACTER VARYING, instrument_sw CHARACTER VARYING, sample_role CHARACTER VARYING, sample_type CHARACTER VARYING, sample_id CHARACTER VARYING, result CHARACTER VARYING, units CHARACTER VARYING, result_status CHARACTER VARYING, username CHARACTER VARYING, flags TEXT [], cntrl_cts JSONB, comments CHARACTER VARYING, dwp_id CHARACTER VARYING, mwp_id CHARACTER VARYING, mwp_position CHARACTER VARYING, start_ts TIMESTAMP WITHOUT TIME ZONE, end_ts TIMESTAMP WITHOUT TIME ZONE)
LANGUAGE SQL
AS $$
SELECT
  assays.assay_name                                      AS assay,
  CONCAT(instruments.model, ' ', instruments.sw_version) AS instrument_sw,
  sample_role,
  sample_type,
  sample_id,
  result,
  units,
  result_status,
  username,
  flags,
  cntrl_cts,
  comments,
  dwp_id,
  mwp_id,
  mwp_position,
  start_ts,
  end_ts
FROM results
  JOIN
  assays ON results.assay_id = assays.id
  JOIN
  instruments ON (SELECT instrument_id
                  FROM runs
                  WHERE id = $1) = instruments.id
WHERE results.run_id = $1;
$$;


