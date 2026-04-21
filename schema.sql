--
-- PostgreSQL database dump
--

\restrict tjsE0ama1gxEWNboVckDlJzPApdpzA95oEqSfQ5JoeDgjE4IEk34NnytKbOO3CA

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_keys (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    key_hash text NOT NULL,
    owner text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    default_model text,
    default_params jsonb,
    meta jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    rpm_limit integer,
    rpd_limit integer,
    spend_cap_usd numeric(12,6),
    provider_key_id uuid
);


--
-- Name: batch_files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.batch_files (
    file_id text NOT NULL,
    owner text NOT NULL,
    key_id uuid NOT NULL,
    model text NOT NULL,
    provider text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: batch_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.batch_jobs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    batch_id text NOT NULL,
    owner text NOT NULL,
    key_id uuid NOT NULL,
    usage_event_id uuid,
    input_file_id text NOT NULL,
    output_file_id text,
    status text DEFAULT 'validating'::text NOT NULL,
    usage_synced boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    model text DEFAULT 'unknown'::text NOT NULL,
    provider text DEFAULT 'openai'::text NOT NULL
);


--
-- Name: checkout_coupons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.checkout_coupons (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    description text,
    discount_type text NOT NULL,
    discount_value numeric(12,2) NOT NULL,
    reuse_policy text DEFAULT 'single_use'::text NOT NULL,
    max_uses integer,
    used_count integer DEFAULT 0 NOT NULL,
    valid_till timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: coupon_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coupon_users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    coupon_id uuid NOT NULL,
    user_id text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: currency_conversion_rates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.currency_conversion_rates (
    currency text NOT NULL,
    rate numeric(18,10) NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    markup_fee numeric(18,4),
    total_rate numeric(18,4),
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: discounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.discounts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id text,
    model_id text,
    discount_pct numeric(5,2) NOT NULL,
    valid_from timestamp with time zone DEFAULT now() NOT NULL,
    valid_until timestamp with time zone,
    label text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    ended_at timestamp with time zone,
    ended_reason character varying(64),
    CONSTRAINT discounts_pct_range CHECK (((discount_pct >= (0)::numeric) AND (discount_pct <= (100)::numeric)))
);


--
-- Name: gstin_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gstin_records (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    payment_event_id uuid NOT NULL,
    gstin text,
    gst_amount numeric(12,2) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: model_prices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_prices (
    model_id text NOT NULL,
    prompt_usd_per_1k numeric(12,8) NOT NULL,
    completion_usd_per_1k numeric(12,8) NOT NULL,
    is_free boolean DEFAULT false NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    provider text NOT NULL,
    is_default boolean NOT NULL,
    upstream_prompt_usd_per_1k numeric(12,8),
    upstream_completion_usd_per_1k numeric(12,8),
    provider_model_id text,
    responses_provider_model_id text,
    supports_batching boolean DEFAULT false NOT NULL,
    supports_embeddings_api boolean DEFAULT false NOT NULL,
    supports_responses_api boolean DEFAULT false NOT NULL,
    supports_completions_api boolean DEFAULT true NOT NULL,
    supports_thinking boolean DEFAULT false NOT NULL
);


--
-- Name: models; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.models (
    model_id text NOT NULL,
    name text NOT NULL,
    context_length integer,
    description text,
    is_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    brand text NOT NULL,
    model_type text DEFAULT 'text'::text NOT NULL,
    input_modalities text[] DEFAULT ARRAY['text'::text] NOT NULL,
    output_modalities text[] DEFAULT ARRAY['text'::text] NOT NULL,
    CONSTRAINT ck_models_model_type CHECK ((model_type = ANY (ARRAY['text'::text, 'embedding'::text, 'image'::text, 'audio'::text, 'video'::text])))
);


--
-- Name: payment_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id text NOT NULL,
    payment_id text NOT NULL,
    provider text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    order_id text,
    currency text,
    amount integer,
    metadata jsonb,
    ip_address text,
    country text,
    amount_usd integer,
    coupon_code text,
    discount_amount integer
);


--
-- Name: provider_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.provider_keys (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    owner text NOT NULL,
    provider text NOT NULL,
    secret_ref text NOT NULL,
    label text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    or_key_hash text
);


--
-- Name: templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.templates (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    owner text,
    description text,
    system text,
    messages jsonb,
    model text,
    params jsonb,
    variables jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: usage_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usage_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    key_id uuid NOT NULL,
    request_id text NOT NULL,
    model text NOT NULL,
    template_id uuid,
    stream boolean DEFAULT false NOT NULL,
    prompt_tokens integer,
    completion_tokens integer,
    total_tokens integer,
    cost_usd numeric(12,8),
    latency_ms integer,
    status text NOT NULL,
    error_code text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    cached_tokens integer,
    upstream_cost_usd numeric(12,8),
    provider text DEFAULT 'openrouter'::text NOT NULL
);


--
-- Name: user_balances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_balances (
    user_id text NOT NULL,
    balance_usd numeric(12,6) DEFAULT '0'::numeric NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id text NOT NULL,
    email text NOT NULL,
    display_name text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- Name: batch_files batch_files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch_files
    ADD CONSTRAINT batch_files_pkey PRIMARY KEY (file_id);


--
-- Name: batch_jobs batch_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch_jobs
    ADD CONSTRAINT batch_jobs_pkey PRIMARY KEY (id);


--
-- Name: checkout_coupons checkout_coupons_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checkout_coupons
    ADD CONSTRAINT checkout_coupons_code_key UNIQUE (code);


--
-- Name: checkout_coupons checkout_coupons_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checkout_coupons
    ADD CONSTRAINT checkout_coupons_pkey PRIMARY KEY (id);


--
-- Name: coupon_users coupon_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_users
    ADD CONSTRAINT coupon_users_pkey PRIMARY KEY (id);


--
-- Name: currency_conversion_rates currency_conversion_rates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.currency_conversion_rates
    ADD CONSTRAINT currency_conversion_rates_pkey PRIMARY KEY (id);


--
-- Name: discounts discounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discounts
    ADD CONSTRAINT discounts_pkey PRIMARY KEY (id);


--
-- Name: gstin_records gstin_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gstin_records
    ADD CONSTRAINT gstin_records_pkey PRIMARY KEY (id);


--
-- Name: model_prices model_prices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_prices
    ADD CONSTRAINT model_prices_pkey PRIMARY KEY (model_id, provider);


--
-- Name: models models_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.models
    ADD CONSTRAINT models_pkey PRIMARY KEY (model_id);


--
-- Name: payment_events payment_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_events
    ADD CONSTRAINT payment_events_pkey PRIMARY KEY (id);


--
-- Name: provider_keys provider_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_keys
    ADD CONSTRAINT provider_keys_pkey PRIMARY KEY (id);


--
-- Name: templates templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.templates
    ADD CONSTRAINT templates_pkey PRIMARY KEY (id);


--
-- Name: api_keys uq_api_keys_key_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT uq_api_keys_key_hash UNIQUE (key_hash);


--
-- Name: coupon_users uq_coupon_users_coupon_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_users
    ADD CONSTRAINT uq_coupon_users_coupon_user UNIQUE (coupon_id, user_id);


--
-- Name: payment_events uq_payment_events_payment_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_events
    ADD CONSTRAINT uq_payment_events_payment_id UNIQUE (payment_id);


--
-- Name: templates uq_templates_owner_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.templates
    ADD CONSTRAINT uq_templates_owner_name UNIQUE (owner, name);


--
-- Name: users uq_users_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email UNIQUE (email);


--
-- Name: usage_events usage_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_events
    ADD CONSTRAINT usage_events_pkey PRIMARY KEY (id);


--
-- Name: user_balances user_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_balances
    ADD CONSTRAINT user_balances_pkey PRIMARY KEY (user_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_api_keys_key_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_api_keys_key_hash ON public.api_keys USING btree (key_hash);


--
-- Name: ix_api_keys_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_keys_owner ON public.api_keys USING btree (owner);


--
-- Name: ix_api_keys_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_keys_status ON public.api_keys USING btree (status);


--
-- Name: ix_batch_files_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batch_files_owner ON public.batch_files USING btree (owner);


--
-- Name: ix_batch_jobs_batch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_batch_jobs_batch_id ON public.batch_jobs USING btree (batch_id);


--
-- Name: ix_batch_jobs_output_file_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batch_jobs_output_file_id ON public.batch_jobs USING btree (output_file_id);


--
-- Name: ix_batch_jobs_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batch_jobs_owner ON public.batch_jobs USING btree (owner);


--
-- Name: ix_batch_jobs_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batch_jobs_provider ON public.batch_jobs USING btree (provider);


--
-- Name: ix_checkout_coupons_active_valid_till; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checkout_coupons_active_valid_till ON public.checkout_coupons USING btree (is_active, valid_till);


--
-- Name: ix_coupon_users_coupon_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coupon_users_coupon_id ON public.coupon_users USING btree (coupon_id);


--
-- Name: ix_coupon_users_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coupon_users_user_id ON public.coupon_users USING btree (user_id);


--
-- Name: ix_currency_conversion_rates_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_currency_conversion_rates_created_at ON public.currency_conversion_rates USING btree (created_at);


--
-- Name: ix_currency_conversion_rates_currency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_currency_conversion_rates_currency ON public.currency_conversion_rates USING btree (currency);


--
-- Name: ix_currency_conversion_rates_currency_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_currency_conversion_rates_currency_created ON public.currency_conversion_rates USING btree (currency, created_at);


--
-- Name: ix_discounts_model_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_discounts_model_id ON public.discounts USING btree (model_id);


--
-- Name: ix_discounts_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_discounts_user_id ON public.discounts USING btree (user_id);


--
-- Name: ix_gstin_records_payment_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gstin_records_payment_event_id ON public.gstin_records USING btree (payment_event_id);


--
-- Name: ix_model_prices_one_default; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_model_prices_one_default ON public.model_prices USING btree (model_id) WHERE (is_default = true);


--
-- Name: ix_models_input_modalities; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_models_input_modalities ON public.models USING gin (input_modalities);


--
-- Name: ix_models_is_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_models_is_enabled ON public.models USING btree (is_enabled);


--
-- Name: ix_models_model_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_models_model_type ON public.models USING btree (model_type);


--
-- Name: ix_models_output_modalities; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_models_output_modalities ON public.models USING gin (output_modalities);


--
-- Name: ix_payment_events_country; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_events_country ON public.payment_events USING btree (country);


--
-- Name: ix_payment_events_coupon_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_events_coupon_code ON public.payment_events USING btree (coupon_code);


--
-- Name: ix_payment_events_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_events_created_at ON public.payment_events USING btree (created_at);


--
-- Name: ix_payment_events_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_events_provider ON public.payment_events USING btree (provider);


--
-- Name: ix_payment_events_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_events_user_created ON public.payment_events USING btree (user_id, created_at);


--
-- Name: ix_payment_events_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_events_user_id ON public.payment_events USING btree (user_id);


--
-- Name: ix_provider_keys_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_keys_owner ON public.provider_keys USING btree (owner);


--
-- Name: ix_provider_keys_owner_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_keys_owner_provider ON public.provider_keys USING btree (owner, provider);


--
-- Name: ix_templates_owner_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_templates_owner_created ON public.templates USING btree (owner, created_at DESC);


--
-- Name: ix_usage_events_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usage_events_created_at ON public.usage_events USING btree (created_at);


--
-- Name: ix_usage_events_key_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usage_events_key_created ON public.usage_events USING btree (key_id, created_at);


--
-- Name: ix_usage_events_model; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usage_events_model ON public.usage_events USING btree (model);


--
-- Name: ix_usage_events_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usage_events_provider ON public.usage_events USING btree (provider);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: uq_templates_global_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_templates_global_name ON public.templates USING btree (name) WHERE (owner IS NULL);


--
-- Name: coupon_users coupon_users_coupon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coupon_users
    ADD CONSTRAINT coupon_users_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES public.checkout_coupons(id) ON DELETE CASCADE;


--
-- Name: gstin_records gstin_records_payment_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gstin_records
    ADD CONSTRAINT gstin_records_payment_event_id_fkey FOREIGN KEY (payment_event_id) REFERENCES public.payment_events(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict tjsE0ama1gxEWNboVckDlJzPApdpzA95oEqSfQ5JoeDgjE4IEk34NnytKbOO3CA

