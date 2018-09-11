--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.7
-- Dumped by pg_dump version 9.6.7

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: results_file(integer); Type: FUNCTION; Schema: public; Owner: admin
--

CREATE FUNCTION results_file(runid integer) RETURNS TABLE(assay character varying, instrument_sw character varying, sample_role character varying, sample_type character varying, sample_id character varying, result character varying, units character varying, result_status character varying, username character varying, flags text[], cntrl_cts jsonb, comments character varying, dwp_id character varying, mwp_id character varying, mwp_position character varying, start_ts timestamp without time zone, end_ts timestamp without time zone)
    LANGUAGE sql
    AS $_$
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
$_$;


ALTER FUNCTION public.results_file(runid integer) OWNER TO admin;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: assays; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE assays (
    id integer NOT NULL,
    instrument_id integer NOT NULL,
    lis_code character varying(10) NOT NULL,
    assay_name character varying(40) NOT NULL
);


ALTER TABLE assays OWNER TO admin;

--
-- Name: assays_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE assays_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE assays_id_seq OWNER TO admin;

--
-- Name: assays_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE assays_id_seq OWNED BY assays.id;


--
-- Name: instruments; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE instruments (
    id integer NOT NULL,
    model character varying(40),
    sn character varying(40),
    sw_version character varying(50)
);


ALTER TABLE instruments OWNER TO admin;

--
-- Name: instruments_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE instruments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE instruments_id_seq OWNER TO admin;

--
-- Name: instruments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE instruments_id_seq OWNED BY instruments.id;


--
-- Name: results; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE results (
    id integer NOT NULL,
    run_id integer NOT NULL,
    assay_id integer NOT NULL,
    sample_role character varying(1) NOT NULL,
    sample_type character varying(10) NOT NULL,
    sample_id character varying(40) NOT NULL,
    result character varying(50) NOT NULL,
    units character varying(10) NOT NULL,
    result_status character varying(1) NOT NULL,
    username character varying(20) NOT NULL,
    flags text[],
    cntrl_cts jsonb,
    comments character varying(255),
    dwp_id character varying(20) NOT NULL,
    mwp_id character varying(20) NOT NULL,
    mwp_position character varying(3) NOT NULL,
    start_ts timestamp without time zone NOT NULL,
    end_ts timestamp without time zone NOT NULL
);


ALTER TABLE results OWNER TO admin;

--
-- Name: results_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE results_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE results_id_seq OWNER TO admin;

--
-- Name: results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE results_id_seq OWNED BY results.id;


--
-- Name: runs; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE runs (
    id integer NOT NULL,
    instrument_id integer NOT NULL,
    msg_ts timestamp with time zone DEFAULT now() NOT NULL,
    msg_guid uuid NOT NULL
);


ALTER TABLE runs OWNER TO admin;

--
-- Name: runs_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE runs_id_seq OWNER TO admin;

--
-- Name: runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE runs_id_seq OWNED BY runs.id;


--
-- Name: assays id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY assays ALTER COLUMN id SET DEFAULT nextval('assays_id_seq'::regclass);


--
-- Name: instruments id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY instruments ALTER COLUMN id SET DEFAULT nextval('instruments_id_seq'::regclass);


--
-- Name: results id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY results ALTER COLUMN id SET DEFAULT nextval('results_id_seq'::regclass);


--
-- Name: runs id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY runs ALTER COLUMN id SET DEFAULT nextval('runs_id_seq'::regclass);


--
-- Name: assays assays_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY assays
    ADD CONSTRAINT assays_pkey PRIMARY KEY (id);


--
-- Name: instruments inst_unique; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY instruments
    ADD CONSTRAINT inst_unique UNIQUE (model, sn, sw_version);


--
-- Name: instruments instruments_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY instruments
    ADD CONSTRAINT instruments_pkey PRIMARY KEY (id);


--
-- Name: results results_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY results
    ADD CONSTRAINT results_pkey PRIMARY KEY (id);


--
-- Name: runs runs_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY runs
    ADD CONSTRAINT runs_pkey PRIMARY KEY (id);


--
-- Name: runs_msg_guid_uindex; Type: INDEX; Schema: public; Owner: admin
--

CREATE UNIQUE INDEX runs_msg_guid_uindex ON runs USING btree (msg_guid);


--
-- Name: assays assays_instrument_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY assays
    ADD CONSTRAINT assays_instrument_id_fkey FOREIGN KEY (instrument_id) REFERENCES instruments(id);


--
-- Name: results results_assay_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY results
    ADD CONSTRAINT results_assay_id_fkey FOREIGN KEY (assay_id) REFERENCES assays(id);


--
-- Name: results results_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY results
    ADD CONSTRAINT results_run_id_fkey FOREIGN KEY (run_id) REFERENCES runs(id);


--
-- Name: runs runs_instrument_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY runs
    ADD CONSTRAINT runs_instrument_id_fkey FOREIGN KEY (instrument_id) REFERENCES instruments(id);


--
-- PostgreSQL database dump complete
--

