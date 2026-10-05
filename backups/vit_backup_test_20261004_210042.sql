PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE markets (
	id VARCHAR(36) NOT NULL,
	market_type VARCHAR(20) NOT NULL,
	category VARCHAR(50),
	title VARCHAR(255) NOT NULL,
	description TEXT,
	status VARCHAR(50),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE edges (
	id INTEGER NOT NULL,
	edge_id VARCHAR NOT NULL,
	description VARCHAR,
	roi FLOAT,
	sample_size INTEGER,
	confidence FLOAT,
	avg_edge FLOAT,
	league VARCHAR,
	home_condition VARCHAR,
	away_condition VARCHAR,
	market VARCHAR,
	status VARCHAR,
	decay_rate FLOAT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	last_updated DATETIME,
	archived_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (edge_id)
);
CREATE TABLE model_performances (
	id INTEGER NOT NULL,
	model_name VARCHAR NOT NULL,
	model_type VARCHAR NOT NULL,
	version INTEGER,
	weight_decay_rate FLOAT,
	min_weight_threshold FLOAT,
	performance_window INTEGER,
	last_weight_update DATETIME,
	consecutive_underperforming INTEGER,
	accuracy_score FLOAT,
	current_weight FLOAT,
	calibration_error FLOAT,
	expected_value FLOAT,
	sharpe_ratio FLOAT,
	positive_clv_rate FLOAT,
	certified BOOLEAN,
	final_score FLOAT,
	last_certified_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	UNIQUE (model_name)
);
CREATE TABLE bankroll_states (
	id INTEGER NOT NULL,
	initial_balance FLOAT,
	current_balance FLOAT,
	peak_balance FLOAT,
	total_staked FLOAT,
	total_profit FLOAT,
	total_bets INTEGER,
	winning_bets INTEGER,
	losing_bets INTEGER,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
CREATE TABLE decision_logs (
	id INTEGER NOT NULL,
	match_id INTEGER,
	prediction_id INTEGER,
	decision_type VARCHAR,
	stake FLOAT,
	odds FLOAT,
	edge FLOAT,
	reason VARCHAR,
	model_contributions TEXT,
	market_context TEXT,
	bankroll_state TEXT,
	timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
CREATE TABLE teams (
	id INTEGER NOT NULL,
	external_id VARCHAR,
	name VARCHAR NOT NULL,
	league VARCHAR,
	country VARCHAR,
	short_name VARCHAR,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE ai_performances (
	id INTEGER NOT NULL,
	source VARCHAR(50) NOT NULL,
	accuracy FLOAT,
	calibration_score FLOAT,
	sample_size INTEGER,
	bias_home_overrate FLOAT,
	bias_draw_overrate FLOAT,
	bias_away_overrate FLOAT,
	league_accuracy JSON,
	current_weight FLOAT,
	last_updated DATETIME,
	total_predictions INTEGER,
	certified BOOLEAN,
	PRIMARY KEY (id),
	UNIQUE (source)
);
CREATE TABLE subscription_plans (
	id INTEGER NOT NULL,
	name VARCHAR(50) NOT NULL,
	display_name VARCHAR(100) NOT NULL,
	price_monthly FLOAT,
	price_yearly FLOAT,
	features JSON,
	prediction_limit INTEGER,
	is_active BOOLEAN,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	UNIQUE (name)
);
CREATE TABLE user_subscriptions (
	id INTEGER NOT NULL,
	api_key_hash VARCHAR(64) NOT NULL,
	plan_name VARCHAR(50) NOT NULL,
	status VARCHAR(20),
	stripe_customer_id VARCHAR(100),
	stripe_subscription_id VARCHAR(100),
	current_period_start DATETIME,
	current_period_end DATETIME,
	prediction_count_today INTEGER,
	prediction_count_reset_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE audit_logs (
	id INTEGER NOT NULL,
	action VARCHAR(100) NOT NULL,
	actor VARCHAR(100),
	resource VARCHAR(100),
	resource_id VARCHAR(100),
	details JSON,
	ip_address VARCHAR(45),
	status VARCHAR(20),
	timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
CREATE TABLE training_datasets (
	id INTEGER NOT NULL,
	filename VARCHAR(255) NOT NULL,
	original_name VARCHAR(255) NOT NULL,
	format VARCHAR(10) NOT NULL,
	record_count INTEGER,
	leagues JSON,
	date_range_start VARCHAR(20),
	date_range_end VARCHAR(20),
	status VARCHAR(20),
	error_message TEXT,
	uploaded_by VARCHAR(100),
	uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	processed_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE users (
	id INTEGER NOT NULL,
	email VARCHAR(255) NOT NULL,
	username VARCHAR(100) NOT NULL,
	hashed_password VARCHAR(255),
	company_name VARCHAR(255),
	phone VARCHAR(50),
	google_id VARCHAR(255),
	telegram_id VARCHAR(255),
	telegram_username VARCHAR(255),
	role VARCHAR(20),
	wallet_address VARCHAR(64),
	admin_role VARCHAR(20),
	subscription_tier VARCHAR(20),
	is_banned BOOLEAN,
	is_active BOOLEAN,
	is_verified BOOLEAN,
	withdrawals_frozen BOOLEAN DEFAULT 'false' NOT NULL,
	is_flagged BOOLEAN DEFAULT 'false' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME,
	last_login DATETIME,
	kyc_status VARCHAR(20),
	kyc_submitted_at DATETIME,
	kyc_data JSON,
	university VARCHAR(255),
	faculty VARCHAR(255),
	department VARCHAR(255),
	study_level VARCHAR(20),
	matric_number VARCHAR(50),
	student_skills JSON,
	student_interests JSON,
	student_country VARCHAR(100),
	is_student_verified BOOLEAN,
	student_profile_completed BOOLEAN,
	current_streak INTEGER,
	best_streak INTEGER,
	total_xp INTEGER,
	failed_login_count INTEGER NOT NULL,
	locked_until DATETIME,
	totp_secret VARCHAR(64),
	totp_secret_pending VARCHAR(64),
	totp_enabled BOOLEAN NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE training_jobs (
	id INTEGER NOT NULL,
	job_id VARCHAR(64) NOT NULL,
	status VARCHAR(20),
	config JSON,
	results JSON,
	summary JSON,
	events JSON,
	progress_pct FLOAT,
	current_model VARCHAR(200),
	total_models INTEGER,
	error_message TEXT,
	data_quality_score FLOAT,
	training_prompt TEXT,
	created_by VARCHAR(100),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	started_at DATETIME,
	completed_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE token_blocklist (
	id INTEGER NOT NULL,
	jti VARCHAR(64) NOT NULL,
	user_id INTEGER,
	reason VARCHAR(50),
	expires_at DATETIME NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
CREATE TABLE wallet_subscription_plans (
	id VARCHAR(36) NOT NULL,
	name VARCHAR(50) NOT NULL,
	description TEXT,
	features JSON,
	price_ngn NUMERIC(10, 2) NOT NULL,
	price_usd NUMERIC(10, 2) NOT NULL,
	price_usdt NUMERIC(10, 2) NOT NULL,
	price_pi NUMERIC(10, 2) NOT NULL,
	price_vitcoin NUMERIC(10, 2) NOT NULL,
	duration_days INTEGER NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (name)
);
CREATE TABLE vitcoin_price_history (
	id VARCHAR(36) NOT NULL,
	price_usd NUMERIC(20, 8) NOT NULL,
	circulating_supply NUMERIC(20, 8) NOT NULL,
	rolling_revenue_usd NUMERIC(20, 8) NOT NULL,
	calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE webhook_events (
	id INTEGER NOT NULL,
	provider VARCHAR(32) NOT NULL,
	event_type VARCHAR(128),
	reference VARCHAR(256),
	amount NUMERIC(20, 8),
	currency VARCHAR(16),
	status VARCHAR(32) NOT NULL,
	sig_verified BOOLEAN,
	outcome VARCHAR(64),
	error_msg TEXT,
	payload_summary JSON,
	received_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE task_categories (
	id INTEGER NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	icon VARCHAR(50),
	color VARCHAR(20),
	sort_order INTEGER NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (name)
);
CREATE TABLE background_task_status (
	id INTEGER NOT NULL,
	task_name VARCHAR(100) NOT NULL,
	status VARCHAR(20),
	restart_count INTEGER,
	last_started_at DATETIME,
	last_crashed_at DATETIME,
	last_error TEXT,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
CREATE TABLE vit_blocks (
	id INTEGER NOT NULL,
	height INTEGER NOT NULL,
	chain_id INTEGER NOT NULL,
	hash VARCHAR(66) NOT NULL,
	parent_hash VARCHAR(66) NOT NULL,
	proposer VARCHAR(255),
	tx_count INTEGER,
	extra_data TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
CREATE TABLE validator_stakes (
	id INTEGER NOT NULL,
	address VARCHAR(255) NOT NULL,
	label VARCHAR(100),
	stake_amount INTEGER NOT NULL,
	active BOOLEAN NOT NULL,
	joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE core_accounts (
	id VARCHAR(36) NOT NULL,
	owner_id VARCHAR(20) NOT NULL,
	account_type VARCHAR(13) NOT NULL,
	name VARCHAR(100),
	metadata_json JSON,
	is_active BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE core_assets (
	id VARCHAR(36) NOT NULL,
	symbol VARCHAR(20) NOT NULL,
	name VARCHAR(100) NOT NULL,
	precision INTEGER NOT NULL,
	asset_type VARCHAR(20) NOT NULL,
	primary_network VARCHAR(50) NOT NULL,
	contract_address VARCHAR(128),
	metadata_json JSON,
	is_active BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE core_wallet_audit (
	id VARCHAR(36) NOT NULL,
	wallet_id VARCHAR(36) NOT NULL,
	action VARCHAR(50) NOT NULL,
	actor_id VARCHAR(100),
	prev_state JSON,
	new_state JSON,
	reference_id VARCHAR(100),
	metadata_json JSON,
	timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE consensus_challenges (
	id VARCHAR(36) NOT NULL,
	epoch INTEGER NOT NULL,
	node_id VARCHAR(255) NOT NULL,
	manifest_id VARCHAR(36) NOT NULL,
	shard_index INTEGER NOT NULL,
	challenge_nonce VARCHAR(64) NOT NULL,
	expected_hash VARCHAR(66) NOT NULL,
	issued_at DATETIME NOT NULL,
	deadline DATETIME NOT NULL,
	status VARCHAR(20) NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE validators (
	node_id VARCHAR(255) NOT NULL,
	public_key VARCHAR(130) NOT NULL,
	status VARCHAR(20) NOT NULL,
	joined_at DATETIME NOT NULL,
	last_active DATETIME NOT NULL,
	extra_metadata JSON,
	PRIMARY KEY (node_id)
);
CREATE TABLE consensus_checkpoints (
	height INTEGER NOT NULL,
	block_hash VARCHAR(66) NOT NULL,
	state_root VARCHAR(66) NOT NULL,
	validator_set_hash VARCHAR(66) NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (height),
	UNIQUE (block_hash)
);
CREATE TABLE consensus_states (
	id VARCHAR(36) NOT NULL,
	node_id VARCHAR(255) NOT NULL,
	height INTEGER NOT NULL,
	round INTEGER NOT NULL,
	state_type VARCHAR(20) NOT NULL,
	block_hash VARCHAR(66) NOT NULL,
	validator_id VARCHAR(255),
	certificate JSON,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE chain_blocks (
	height INTEGER NOT NULL,
	block_hash VARCHAR(64) NOT NULL,
	prev_hash VARCHAR(64),
	merkle_root VARCHAR(64),
	state_root VARCHAR(64),
	timestamp INTEGER,
	validator_id VARCHAR(64),
	validator_signature VARCHAR(256),
	tx_count INTEGER,
	total_fees NUMERIC(36, 18),
	block_reward NUMERIC(36, 18),
	raw_data JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (height)
);
CREATE TABLE chain_accounts (
	address VARCHAR(64) NOT NULL,
	balance NUMERIC(36, 18),
	staked NUMERIC(36, 18),
	nonce INTEGER,
	first_seen_height INTEGER,
	last_active_height INTEGER,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (address)
);
CREATE TABLE p2p_peers (
	node_id VARCHAR(43) NOT NULL,
	public_key VARCHAR(130) NOT NULL,
	ip_address VARCHAR(45) NOT NULL,
	ws_port INTEGER,
	node_type VARCHAR(20),
	capabilities JSON,
	chain_height INTEGER,
	last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
	last_ping_ms INTEGER,
	is_bootstrap BOOLEAN,
	is_active BOOLEAN,
	country_code VARCHAR(2),
	region VARCHAR(50),
	score FLOAT,
	PRIMARY KEY (node_id)
);
CREATE TABLE authz_permissions (
	id INTEGER NOT NULL,
	slug VARCHAR(100) NOT NULL,
	description TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE authz_roles (
	id INTEGER NOT NULL,
	name VARCHAR(100) NOT NULL,
	slug VARCHAR(100) NOT NULL,
	description TEXT,
	parent_id INTEGER,
	is_builtin BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(parent_id) REFERENCES authz_roles (id)
);
CREATE TABLE authz_resources (
	id INTEGER NOT NULL,
	slug VARCHAR(100) NOT NULL,
	type VARCHAR(50) NOT NULL,
	description TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE authz_policies (
	id INTEGER NOT NULL,
	name VARCHAR(150) NOT NULL,
	description TEXT,
	effect VARCHAR(10) NOT NULL,
	action_pattern VARCHAR(100) NOT NULL,
	resource_pattern VARCHAR(100) NOT NULL,
	conditions JSON NOT NULL,
	priority INTEGER NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE global_identities (
	id INTEGER NOT NULL,
	gid VARCHAR(64) NOT NULL,
	type VARCHAR(15) NOT NULL,
	status VARCHAR(9) NOT NULL,
	verification_status VARCHAR(10) NOT NULL,
	username VARCHAR(100),
	email VARCHAR(255),
	phone VARCHAR(50),
	display_name VARCHAR(150),
	profile JSON NOT NULL,
	auth_methods JSON NOT NULL,
	security_metadata JSON NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE oracle_results (
	id VARCHAR(36) NOT NULL,
	match_id VARCHAR(100) NOT NULL,
	source VARCHAR(100) NOT NULL,
	home_score INTEGER NOT NULL,
	away_score INTEGER NOT NULL,
	result VARCHAR(10) NOT NULL,
	submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	is_accepted BOOLEAN NOT NULL,
	dispute_flag BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_oracle_match_source UNIQUE (match_id, source)
);
CREATE TABLE blockchain_transactions (
	id VARCHAR(36) NOT NULL,
	tx_type VARCHAR(40) NOT NULL,
	entity_type VARCHAR(40) NOT NULL,
	entity_id VARCHAR(100) NOT NULL,
	match_id VARCHAR(100),
	amount NUMERIC(20, 8) NOT NULL,
	currency VARCHAR(10) NOT NULL,
	meta JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE marketplace_signals (
	id VARCHAR(36) NOT NULL,
	category VARCHAR(50) NOT NULL,
	title VARCHAR(200) NOT NULL,
	description TEXT,
	confidence INTEGER NOT NULL,
	price_vit NUMERIC(20, 8) NOT NULL,
	provider VARCHAR(100) NOT NULL,
	external_id VARCHAR(100),
	is_active BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE model_metadata (
	id INTEGER NOT NULL,
	"key" VARCHAR(64) NOT NULL,
	name VARCHAR(128) NOT NULL,
	model_type VARCHAR(64) NOT NULL,
	version VARCHAR(32),
	weight FLOAT,
	accuracy FLOAT,
	accuracy_1x2 FLOAT,
	accuracy_ou FLOAT,
	brier_score FLOAT,
	log_loss FLOAT,
	clv_score FLOAT,
	clv_samples INTEGER,
	clv_negative_streak_days INTEGER,
	last_clv_check_at DATETIME,
	predictions_total INTEGER,
	predictions_correct INTEGER,
	is_active BOOLEAN,
	auto_demoted BOOLEAN,
	pkl_loaded BOOLEAN,
	pkl_path VARCHAR(512),
	training_samples INTEGER,
	active_version VARCHAR(32),
	version_history JSON,
	supported_markets JSON,
	description TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_model_metadata_key UNIQUE ("key")
);
CREATE TABLE ai_prediction_audit (
	id INTEGER NOT NULL,
	match_id VARCHAR(128) NOT NULL,
	home_team VARCHAR(128),
	away_team VARCHAR(128),
	home_prob FLOAT NOT NULL,
	draw_prob FLOAT NOT NULL,
	away_prob FLOAT NOT NULL,
	over_25_prob FLOAT,
	btts_prob FLOAT,
	confidence FLOAT,
	risk_score FLOAT,
	model_agreement FLOAT,
	individual_results JSON,
	weights_snapshot JSON,
	pkl_models_active INTEGER,
	triggered_by VARCHAR(64),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
CREATE TABLE ai_insights (
	id INTEGER NOT NULL,
	match_id INTEGER NOT NULL,
	insights JSON NOT NULL,
	original JSON,
	uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE polling_data (
	id INTEGER NOT NULL,
	election_id INTEGER NOT NULL,
	source VARCHAR(100) NOT NULL,
	data JSON NOT NULL,
	timestamp DATETIME NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE elections (
	id VARCHAR(36) NOT NULL,
	title VARCHAR(255) NOT NULL,
	country VARCHAR(3) NOT NULL,
	election_type VARCHAR(13) NOT NULL,
	election_date DATE NOT NULL,
	status VARCHAR(9) NOT NULL,
	description TEXT,
	total_seats INTEGER,
	metadata JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
CREATE TABLE policy_proposals (
	id VARCHAR(36) NOT NULL,
	title VARCHAR(255) NOT NULL,
	jurisdiction VARCHAR(255) NOT NULL,
	category VARCHAR(11) NOT NULL,
	description TEXT NOT NULL,
	sponsor VARCHAR(255) NOT NULL,
	status VARCHAR(8) NOT NULL,
	impact_scores JSON,
	metadata JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
CREATE TABLE policy_impacts (
	id INTEGER NOT NULL,
	title VARCHAR(200) NOT NULL,
	description TEXT NOT NULL,
	category VARCHAR(100) NOT NULL,
	severity VARCHAR(50) NOT NULL,
	predicted_impact TEXT NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE policy_scenarios (
	id INTEGER NOT NULL,
	name VARCHAR(200) NOT NULL,
	variables JSON NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE campus_circles (
	id INTEGER NOT NULL,
	name VARCHAR(150) NOT NULL,
	description TEXT,
	circle_type VARCHAR(32) NOT NULL,
	university VARCHAR(255) NOT NULL,
	faculty VARCHAR(255),
	department VARCHAR(255),
	member_count INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_circle_name_uni UNIQUE (name, university)
);
CREATE TABLE dev_api_plans (
	id INTEGER NOT NULL,
	name VARCHAR(32) NOT NULL,
	display_name VARCHAR(64) NOT NULL,
	rate_limit_rpm INTEGER NOT NULL,
	rate_limit_rpd INTEGER NOT NULL,
	price_vitcoin_per_1k NUMERIC(20, 8) NOT NULL,
	description TEXT,
	is_active BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (name)
);
CREATE TABLE strategy_vaults (
	id INTEGER NOT NULL,
	name VARCHAR(128) NOT NULL,
	slug VARCHAR(128) NOT NULL,
	description VARCHAR(512),
	strategy_filter JSON NOT NULL,
	historical_roi NUMERIC(10, 4) NOT NULL,
	win_rate NUMERIC(5, 4) NOT NULL,
	total_staked NUMERIC(20, 8) NOT NULL,
	max_cap NUMERIC(20, 8) NOT NULL,
	status VARCHAR(32) NOT NULL,
	created_at DATETIME NOT NULL,
	last_rebalanced_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (name),
	UNIQUE (slug)
);
CREATE TABLE social_signals (
	id VARCHAR(36) NOT NULL,
	source VARCHAR(100) NOT NULL,
	url VARCHAR(500),
	title VARCHAR(255) NOT NULL,
	summary TEXT,
	topic VARCHAR(100),
	entities JSON,
	evidence JSON,
	freshness_seconds INTEGER,
	confidence FLOAT,
	verification_status VARCHAR(50),
	deduplication_key VARCHAR(255) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE bridge_pools (
	id INTEGER NOT NULL,
	asset_from VARCHAR(16) NOT NULL,
	asset_to VARCHAR(16) NOT NULL,
	chain_from VARCHAR(32) NOT NULL,
	chain_to VARCHAR(32) NOT NULL,
	exchange_rate NUMERIC(20, 8) NOT NULL,
	fee_pct NUMERIC(10, 4) NOT NULL,
	min_amount NUMERIC(20, 8) NOT NULL,
	max_amount NUMERIC(20, 8) NOT NULL,
	pool_liquidity NUMERIC(20, 8) NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE treasury_pools (
	id INTEGER NOT NULL,
	pool_type VARCHAR(20) NOT NULL,
	balance NUMERIC(20, 6) NOT NULL,
	total_deposited NUMERIC(20, 6) NOT NULL,
	total_spent NUMERIC(20, 6) NOT NULL,
	allocation_pct NUMERIC(5, 2) NOT NULL,
	auto_refill BOOLEAN NOT NULL,
	refill_threshold NUMERIC(20, 6) NOT NULL,
	refill_amount NUMERIC(20, 6) NOT NULL,
	description TEXT,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (pool_type)
);
CREATE TABLE ai_model_attestations (
	id INTEGER NOT NULL,
	model_id VARCHAR(100) NOT NULL,
	model_name VARCHAR(200) NOT NULL,
	provider VARCHAR(80) NOT NULL,
	version VARCHAR(50) NOT NULL,
	capability_hash VARCHAR(66) NOT NULL,
	public_key TEXT,
	accuracy_score NUMERIC(5, 4),
	total_outputs INTEGER NOT NULL,
	verified_outputs INTEGER NOT NULL,
	disputed_outputs INTEGER NOT NULL,
	is_active BOOLEAN NOT NULL,
	registered_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (model_id)
);
CREATE TABLE iq_test_questions (
	id INTEGER NOT NULL,
	q TEXT NOT NULL,
	options JSON NOT NULL,
	correct INTEGER NOT NULL,
	explanation TEXT,
	is_active BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE oracle_mic_episodes (
	id VARCHAR(36) NOT NULL,
	title VARCHAR(255) NOT NULL,
	host VARCHAR(100) NOT NULL,
	date VARCHAR(50) NOT NULL,
	length VARCHAR(20) NOT NULL,
	premium BOOLEAN NOT NULL,
	is_active BOOLEAN NOT NULL,
	sort_order INTEGER NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE sub_chains (
	id INTEGER NOT NULL,
	chain_type VARCHAR(11) NOT NULL,
	name VARCHAR(100) NOT NULL,
	chain_id VARCHAR(32) NOT NULL,
	status VARCHAR(9) NOT NULL,
	current_block INTEGER NOT NULL,
	finalized_block INTEGER NOT NULL,
	block_time_ms INTEGER NOT NULL,
	validator_count INTEGER NOT NULL,
	tps_target INTEGER NOT NULL,
	tps_current NUMERIC(10, 2) NOT NULL,
	total_txns INTEGER NOT NULL,
	genesis_hash VARCHAR(66),
	latest_block_hash VARCHAR(66),
	description TEXT,
	config TEXT NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (chain_type),
	UNIQUE (chain_id)
);
CREATE TABLE prophecy_chapters (
	id INTEGER NOT NULL,
	title VARCHAR(200) NOT NULL,
	description TEXT,
	sequence_order INTEGER,
	required_predictions INTEGER,
	required_accuracy FLOAT,
	required_streak INTEGER,
	reward_vit INTEGER,
	reward_xp INTEGER,
	reward_badge VARCHAR(100),
	is_active BOOLEAN,
	created_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE node_activities (
	id VARCHAR(36) NOT NULL,
	node_id VARCHAR(255) NOT NULL,
	node_name VARCHAR(100) NOT NULL,
	node_type VARCHAR(20) NOT NULL,
	activity_type VARCHAR(50) NOT NULL,
	contribution_score FLOAT NOT NULL,
	activity_meta JSON,
	recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE network_snapshots (
	id VARCHAR(36) NOT NULL,
	total_nodes INTEGER NOT NULL,
	active_nodes INTEGER NOT NULL,
	total_contributions INTEGER NOT NULL,
	oracle_submissions INTEGER NOT NULL,
	validator_predictions INTEGER NOT NULL,
	network_health_score FLOAT NOT NULL,
	growth_rate_24h FLOAT NOT NULL,
	top_nodes JSON,
	snapshot_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
);
CREATE TABLE match_feature_store (
	id INTEGER NOT NULL,
	match_id VARCHAR NOT NULL,
	home_team VARCHAR NOT NULL,
	away_team VARCHAR NOT NULL,
	league VARCHAR NOT NULL,
	kickoff_time DATETIME,
	features JSON NOT NULL,
	odds_snapshot JSON,
	injury_snapshot JSON,
	source_quality FLOAT,
	pipeline_version VARCHAR,
	is_stale BOOLEAN,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
);
CREATE TABLE pipeline_runs (
	id INTEGER NOT NULL,
	run_type VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	leagues_processed JSON,
	matches_upserted INTEGER,
	matches_skipped INTEGER,
	errors JSON,
	duration_seconds FLOAT,
	started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	finished_at DATETIME,
	PRIMARY KEY (id)
);
CREATE TABLE matches (
	id INTEGER NOT NULL,
	market_id VARCHAR(36),
	market_type VARCHAR(20) NOT NULL,
	external_id VARCHAR,
	home_team VARCHAR NOT NULL,
	away_team VARCHAR NOT NULL,
	league VARCHAR NOT NULL,
	kickoff_time DATETIME NOT NULL,
	status VARCHAR,
	sport VARCHAR(32),
	source VARCHAR(32),
	fingerprint VARCHAR(255),
	home_goals INTEGER,
	away_goals INTEGER,
	actual_outcome VARCHAR,
	statistics JSON,
	opening_odds_home FLOAT,
	opening_odds_draw FLOAT,
	opening_odds_away FLOAT,
	closing_odds_home FLOAT,
	closing_odds_draw FLOAT,
	closing_odds_away FLOAT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(market_id) REFERENCES markets (id)
);
CREATE TABLE training_guide_steps (
	id INTEGER NOT NULL,
	job_id_fk INTEGER NOT NULL,
	step_number INTEGER NOT NULL,
	step_name VARCHAR(100) NOT NULL,
	description TEXT,
	status VARCHAR(20),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(job_id_fk) REFERENCES training_jobs (id)
);
CREATE TABLE email_tokens (
	id INTEGER NOT NULL,
	token_hash VARCHAR(64) NOT NULL,
	user_id INTEGER NOT NULL,
	purpose VARCHAR(20) NOT NULL,
	expires_at DATETIME NOT NULL,
	used_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE wallets (
	id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	ngn_balance NUMERIC(20, 8) NOT NULL,
	usd_balance NUMERIC(20, 8) NOT NULL,
	usdt_balance NUMERIC(20, 8) NOT NULL,
	pi_balance NUMERIC(20, 8) NOT NULL,
	vitcoin_balance NUMERIC(20, 8) NOT NULL,
	staked_vitcoin_balance NUMERIC(20, 8) NOT NULL,
	tx_metadata JSON,
	is_frozen BOOLEAN NOT NULL,
	kyc_verified BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE platform_configs (
	id VARCHAR(36) NOT NULL,
	"key" VARCHAR(100) NOT NULL,
	value JSON NOT NULL,
	description TEXT,
	updated_by INTEGER,
	updated_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	UNIQUE ("key"),
	FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE TABLE platform_secrets (
	id VARCHAR(36) NOT NULL,
	"key" VARCHAR(100) NOT NULL,
	encrypted_value TEXT NOT NULL,
	updated_by INTEGER,
	updated_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE TABLE notifications (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	type VARCHAR(19) NOT NULL,
	title VARCHAR(255) NOT NULL,
	body TEXT NOT NULL,
	is_read BOOLEAN NOT NULL,
	channel VARCHAR(9) NOT NULL,
	category VARCHAR(32) NOT NULL,
	priority VARCHAR(16) NOT NULL,
	payload_metadata TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE notification_preferences (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	prediction_alerts BOOLEAN NOT NULL,
	match_results BOOLEAN NOT NULL,
	wallet_activity BOOLEAN NOT NULL,
	validator_rewards BOOLEAN NOT NULL,
	subscription_expiry BOOLEAN NOT NULL,
	validator_status BOOLEAN NOT NULL,
	email_enabled BOOLEAN NOT NULL,
	telegram_enabled BOOLEAN NOT NULL,
	in_app_enabled BOOLEAN NOT NULL,
	categories_enabled TEXT,
	priorities_enabled TEXT,
	telegram_chat_id VARCHAR(64),
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE push_subscriptions (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	endpoint VARCHAR(512) NOT NULL,
	p256dh VARCHAR(256) NOT NULL,
	auth VARCHAR(256) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	UNIQUE (endpoint)
);
CREATE TABLE user_trust_scores (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	transaction_score FLOAT NOT NULL,
	prediction_score FLOAT NOT NULL,
	activity_score FLOAT NOT NULL,
	fraud_penalty FLOAT NOT NULL,
	composite_score FLOAT NOT NULL,
	risk_tier VARCHAR(16) NOT NULL,
	total_flags INTEGER NOT NULL,
	open_flags INTEGER NOT NULL,
	last_calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE fraud_flags (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	flagged_by VARCHAR(32) NOT NULL,
	category VARCHAR(32) NOT NULL,
	severity VARCHAR(16) NOT NULL,
	rule_code VARCHAR(64) NOT NULL,
	title VARCHAR(128) NOT NULL,
	detail TEXT,
	status VARCHAR(20) NOT NULL,
	reviewed_by_id INTEGER,
	reviewed_at DATETIME,
	resolution_note TEXT,
	evidence_json TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(reviewed_by_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE risk_events (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	rule_code VARCHAR(64) NOT NULL,
	score_impact FLOAT NOT NULL,
	detail TEXT,
	evidence_json TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE identity_organizations (
	id INTEGER NOT NULL,
	name VARCHAR(150) NOT NULL,
	slug VARCHAR(100) NOT NULL,
	owner_id INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE identity_workspace_settings (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	"key" VARCHAR(100) NOT NULL,
	value JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_identity_workspace_setting_user_key UNIQUE (user_id, "key"),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE system_ids (
	id INTEGER NOT NULL,
	sid VARCHAR(20) NOT NULL,
	user_id INTEGER NOT NULL,
	display_name VARCHAR(150) NOT NULL,
	tier VARCHAR(8) NOT NULL,
	avatar_initials VARCHAR(4) NOT NULL,
	did VARCHAR(255),
	badges JSON NOT NULL,
	issued_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	expires_at DATETIME,
	revoked BOOLEAN NOT NULL,
	revoked_reason TEXT,
	updated_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	UNIQUE (sid),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE student_profiles (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	bio TEXT,
	expected_graduation_year INTEGER,
	gpa FLOAT,
	total_resources_uploaded INTEGER NOT NULL,
	total_resources_verified INTEGER NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE tasks (
	id INTEGER NOT NULL,
	category_id INTEGER NOT NULL,
	title VARCHAR(200) NOT NULL,
	description TEXT NOT NULL,
	short_description VARCHAR(100),
	task_type VARCHAR(8) NOT NULL,
	status VARCHAR(8) NOT NULL,
	required_count INTEGER NOT NULL,
	max_completions INTEGER NOT NULL,
	vit_reward NUMERIC(20, 8) NOT NULL,
	xp_reward INTEGER NOT NULL,
	expires_at DATETIME,
	reset_period_days INTEGER,
	icon VARCHAR(50),
	color VARCHAR(20),
	sort_order INTEGER NOT NULL,
	is_featured BOOLEAN NOT NULL,
	requirements JSON NOT NULL,
	action_url VARCHAR(200),
	action_label VARCHAR(50),
	created_by INTEGER NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(category_id) REFERENCES task_categories (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE slash_events (
	id INTEGER NOT NULL,
	validator_address VARCHAR(255) NOT NULL,
	reason VARCHAR(32) NOT NULL,
	slash_amount INTEGER NOT NULL,
	stake_before INTEGER NOT NULL,
	stake_after INTEGER NOT NULL,
	evidence TEXT,
	appeal_deadline_slot INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(validator_address) REFERENCES validator_stakes (address)
);
CREATE TABLE core_wallets (
	id VARCHAR(36) NOT NULL,
	account_id VARCHAR(36) NOT NULL,
	name VARCHAR(100) NOT NULL,
	status VARCHAR(8) NOT NULL,
	can_deposit BOOLEAN NOT NULL,
	can_withdraw BOOLEAN NOT NULL,
	can_transfer BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(account_id) REFERENCES core_accounts (id) ON DELETE CASCADE
);
CREATE TABLE content_hash_registry (
	id INTEGER NOT NULL,
	content_hash VARCHAR(66) NOT NULL,
	ipfs_cid VARCHAR(120),
	arweave_id VARCHAR(120),
	content_type VARCHAR(100) NOT NULL,
	size_bytes INTEGER,
	description TEXT,
	owner_user_id INTEGER,
	ref_type VARCHAR(80),
	ref_id INTEGER,
	replication_factor INTEGER NOT NULL,
	availability_score NUMERIC(5, 4) NOT NULL,
	is_public BOOLEAN NOT NULL,
	pinned BOOLEAN NOT NULL,
	anchor_block INTEGER,
	anchor_tx VARCHAR(66),
	registered_at DATETIME NOT NULL,
	last_verified_at DATETIME,
	is_tachyon BOOLEAN NOT NULL,
	tachyon_shards INTEGER,
	tachyon_parity_shards INTEGER,
	quantum_state_hash VARCHAR(66),
	PRIMARY KEY (id),
	UNIQUE (content_hash),
	FOREIGN KEY(owner_user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE tachyon_manifests (
	file_id VARCHAR(36) NOT NULL,
	filename VARCHAR(512) NOT NULL,
	size_bytes INTEGER NOT NULL,
	fragment_names JSON NOT NULL,
	provider_mapping JSON NOT NULL,
	owner_user_id INTEGER,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (file_id),
	FOREIGN KEY(owner_user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE user_storage_nodes (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	provider VARCHAR(32) NOT NULL,
	alias VARCHAR(128) NOT NULL,
	config_key VARCHAR(256) NOT NULL,
	status VARCHAR(32) NOT NULL,
	gb_contributed NUMERIC(14, 4) NOT NULL,
	quota_bytes NUMERIC(20, 0) NOT NULL,
	gb_used NUMERIC(14, 4) NOT NULL,
	tsc_earned NUMERIC(20, 8) NOT NULL,
	tsc_pending NUMERIC(20, 8) NOT NULL,
	reliability_score NUMERIC(5, 4) NOT NULL,
	verification_count INTEGER NOT NULL,
	verification_pass INTEGER NOT NULL,
	last_verified_at DATETIME,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	UNIQUE (config_key)
);
CREATE TABLE consensus_responses (
	id VARCHAR(36) NOT NULL,
	challenge_id VARCHAR(36) NOT NULL,
	node_id VARCHAR(255) NOT NULL,
	response_hash VARCHAR(66) NOT NULL,
	response_signature TEXT NOT NULL,
	responded_at DATETIME NOT NULL,
	is_correct BOOLEAN,
	latency_ms INTEGER,
	PRIMARY KEY (id),
	UNIQUE (challenge_id),
	FOREIGN KEY(challenge_id) REFERENCES consensus_challenges (id) ON DELETE CASCADE
);
CREATE TABLE validator_reputation (
	node_id VARCHAR(255) NOT NULL,
	score FLOAT NOT NULL,
	blocks_produced INTEGER NOT NULL,
	blocks_missed INTEGER NOT NULL,
	consecutive_misses INTEGER NOT NULL,
	uptime_pct FLOAT NOT NULL,
	PRIMARY KEY (node_id),
	FOREIGN KEY(node_id) REFERENCES validators (node_id) ON DELETE CASCADE
);
CREATE TABLE chain_transactions (
	tx_hash VARCHAR(64) NOT NULL,
	block_height INTEGER,
	from_address VARCHAR(64),
	to_address VARCHAR(64),
	amount NUMERIC(36, 18),
	nonce INTEGER,
	gas_fee NUMERIC(36, 18),
	tx_type VARCHAR(20),
	data JSON,
	signature VARCHAR(256),
	timestamp INTEGER,
	status VARCHAR(20),
	PRIMARY KEY (tx_hash),
	FOREIGN KEY(block_height) REFERENCES chain_blocks (height)
);
CREATE TABLE authz_user_roles (
	user_id INTEGER NOT NULL,
	role_id INTEGER NOT NULL,
	PRIMARY KEY (user_id, role_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(role_id) REFERENCES authz_roles (id) ON DELETE CASCADE
);
CREATE TABLE authz_role_permissions (
	role_id INTEGER NOT NULL,
	permission_id INTEGER NOT NULL,
	PRIMARY KEY (role_id, permission_id),
	FOREIGN KEY(role_id) REFERENCES authz_roles (id) ON DELETE CASCADE,
	FOREIGN KEY(permission_id) REFERENCES authz_permissions (id) ON DELETE CASCADE
);
CREATE TABLE identity_sessions (
	id INTEGER NOT NULL,
	identity_id INTEGER NOT NULL,
	session_token VARCHAR(255) NOT NULL,
	refresh_token VARCHAR(255),
	device_id VARCHAR(100),
	ip_address VARCHAR(45),
	user_agent TEXT,
	is_active BOOLEAN NOT NULL,
	expires_at DATETIME NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	last_activity DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(identity_id) REFERENCES global_identities (id) ON DELETE CASCADE
);
CREATE TABLE trusted_devices (
	id INTEGER NOT NULL,
	identity_id INTEGER NOT NULL,
	device_id VARCHAR(100) NOT NULL,
	platform VARCHAR(50),
	browser VARCHAR(50),
	is_trusted BOOLEAN NOT NULL,
	risk_score INTEGER NOT NULL,
	last_ip VARCHAR(45),
	last_active DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(identity_id) REFERENCES global_identities (id) ON DELETE CASCADE
);
CREATE TABLE validator_profiles (
	id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	stake_amount NUMERIC(20, 8) NOT NULL,
	trust_score NUMERIC(5, 4) NOT NULL,
	total_predictions INTEGER NOT NULL,
	accurate_predictions INTEGER NOT NULL,
	influence_score NUMERIC(20, 8) NOT NULL,
	status VARCHAR(20) NOT NULL,
	joined_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	last_active DATETIME,
	category_reputation JSON,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE consensus_predictions (
	id VARCHAR(36) NOT NULL,
	market_id VARCHAR(36),
	match_id VARCHAR(100) NOT NULL,
	match_data JSON,
	ai_p_home NUMERIC(5, 4) NOT NULL,
	ai_p_draw NUMERIC(5, 4) NOT NULL,
	ai_p_away NUMERIC(5, 4) NOT NULL,
	ai_confidence NUMERIC(5, 4) NOT NULL,
	ai_risk NUMERIC(5, 4) NOT NULL,
	ai_outcomes JSON,
	category VARCHAR(50) NOT NULL,
	validator_count INTEGER NOT NULL,
	consensus_p_home NUMERIC(5, 4) NOT NULL,
	consensus_p_draw NUMERIC(5, 4) NOT NULL,
	consensus_p_away NUMERIC(5, 4) NOT NULL,
	consensus_outcomes JSON,
	final_p_home NUMERIC(5, 4) NOT NULL,
	final_p_draw NUMERIC(5, 4) NOT NULL,
	final_p_away NUMERIC(5, 4) NOT NULL,
	final_outcomes JSON,
	total_influence NUMERIC(20, 8) NOT NULL,
	status VARCHAR(20) NOT NULL,
	published_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	settled_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (market_id),
	FOREIGN KEY(market_id) REFERENCES markets (id),
	UNIQUE (match_id)
);
CREATE TABLE user_stakes (
	id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	market_id VARCHAR(36) NOT NULL,
	match_id VARCHAR(100),
	prediction VARCHAR(20) NOT NULL,
	stake_amount NUMERIC(20, 8) NOT NULL,
	currency VARCHAR(10) NOT NULL,
	status VARCHAR(20) NOT NULL,
	payout_amount NUMERIC(20, 8) NOT NULL,
	category VARCHAR(50) NOT NULL,
	ah_line NUMERIC(5, 2),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(market_id) REFERENCES markets (id)
);
CREATE TABLE oracle_disputes (
	id VARCHAR(36) NOT NULL,
	match_id VARCHAR(100) NOT NULL,
	source_a VARCHAR(100) NOT NULL,
	result_a VARCHAR(10) NOT NULL,
	source_b VARCHAR(100) NOT NULL,
	result_b VARCHAR(10) NOT NULL,
	resolution VARCHAR(10),
	resolved_by INTEGER,
	resolution_note TEXT,
	status VARCHAR(20) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	resolved_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(resolved_by) REFERENCES users (id)
);
CREATE TABLE agent_applications (
	id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	agent_type VARCHAR(20) NOT NULL,
	business_name VARCHAR(200),
	location VARCHAR(200) NOT NULL,
	status VARCHAR(20) NOT NULL,
	commission_rate NUMERIC(5, 4) NOT NULL,
	applied_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	reviewed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE gov_proposals (
	id INTEGER NOT NULL,
	market_id VARCHAR(36),
	proposer_id INTEGER NOT NULL,
	title VARCHAR(256) NOT NULL,
	description TEXT NOT NULL,
	category VARCHAR(64) NOT NULL,
	change_payload TEXT,
	status VARCHAR(20) NOT NULL,
	voting_starts_at DATETIME,
	voting_ends_at DATETIME,
	timelock_seconds INTEGER NOT NULL,
	executed_at DATETIME,
	execution_note TEXT,
	votes_for FLOAT NOT NULL,
	votes_against FLOAT NOT NULL,
	votes_abstain FLOAT NOT NULL,
	quorum_required FLOAT NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(market_id) REFERENCES markets (id),
	FOREIGN KEY(proposer_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE gov_configs (
	id INTEGER NOT NULL,
	"key" VARCHAR(64) NOT NULL,
	value TEXT NOT NULL,
	data_type VARCHAR(16) NOT NULL,
	description TEXT,
	updated_by INTEGER,
	updated_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	UNIQUE ("key"),
	FOREIGN KEY(updated_by) REFERENCES users (id)
);
CREATE TABLE merit_scores (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	score NUMERIC(16, 4) NOT NULL,
	tier VARCHAR(9) NOT NULL,
	peak_score NUMERIC(16, 4) NOT NULL,
	peak_tier VARCHAR(9) NOT NULL,
	total_earned NUMERIC(16, 4) NOT NULL,
	total_lost NUMERIC(16, 4) NOT NULL,
	streak_days INTEGER NOT NULL,
	last_activity_at DATETIME,
	last_decay_at DATETIME,
	bonus_vit_earned NUMERIC(20, 6) NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE election_events (
	id INTEGER NOT NULL,
	market_id VARCHAR(36),
	title VARCHAR(200) NOT NULL,
	country VARCHAR(100) NOT NULL,
	date DATETIME NOT NULL,
	status VARCHAR(50) NOT NULL,
	candidates JSON NOT NULL,
	sentiment_data JSON,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(market_id) REFERENCES markets (id)
);
CREATE TABLE candidates (
	id VARCHAR(36) NOT NULL,
	election_id VARCHAR(36) NOT NULL,
	name VARCHAR(255) NOT NULL,
	party VARCHAR(255) NOT NULL,
	position VARCHAR(255),
	bio TEXT,
	polling_avg FLOAT NOT NULL,
	win_probability FLOAT NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(election_id) REFERENCES elections (id) ON DELETE CASCADE
);
CREATE TABLE election_polls (
	id VARCHAR(36) NOT NULL,
	election_id VARCHAR(36) NOT NULL,
	pollster VARCHAR(255) NOT NULL,
	conducted_date DATE NOT NULL,
	sample_size INTEGER NOT NULL,
	methodology VARCHAR(255),
	margin_of_error FLOAT NOT NULL,
	results JSON NOT NULL,
	weight FLOAT NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(election_id) REFERENCES elections (id) ON DELETE CASCADE
);
CREATE TABLE remittance_transactions (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	amount NUMERIC(20, 8) NOT NULL,
	currency VARCHAR(10) NOT NULL,
	direction VARCHAR(10) NOT NULL,
	status VARCHAR(50) NOT NULL,
	note TEXT,
	reference VARCHAR(100),
	recipient_address VARCHAR(255),
	sender_address VARCHAR(255),
	created_at DATETIME NOT NULL,
	currency_from VARCHAR(10),
	currency_to VARCHAR(10),
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE academic_courses (
	id INTEGER NOT NULL,
	course_code VARCHAR(20) NOT NULL,
	course_title VARCHAR(255) NOT NULL,
	description TEXT,
	university VARCHAR(255) NOT NULL,
	faculty VARCHAR(255) NOT NULL,
	department VARCHAR(255) NOT NULL,
	level VARCHAR(20) NOT NULL,
	upvotes INTEGER,
	is_verified BOOLEAN,
	created_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_course_code_uni UNIQUE (course_code, university),
	FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE TABLE campus_posts (
	id INTEGER NOT NULL,
	circle_id INTEGER NOT NULL,
	author_id INTEGER NOT NULL,
	content TEXT NOT NULL,
	media_urls JSON,
	upvotes INTEGER,
	is_pinned BOOLEAN,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(circle_id) REFERENCES campus_circles (id),
	FOREIGN KEY(author_id) REFERENCES users (id)
);
CREATE TABLE campus_gigs (
	id INTEGER NOT NULL,
	title VARCHAR(255) NOT NULL,
	description TEXT NOT NULL,
	gig_type VARCHAR(50) NOT NULL,
	budget_vit FLOAT,
	budget_ngn FLOAT,
	university VARCHAR(255) NOT NULL,
	status VARCHAR(20),
	posted_by INTEGER NOT NULL,
	assigned_to INTEGER,
	deadline DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	completed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(posted_by) REFERENCES users (id),
	FOREIGN KEY(assigned_to) REFERENCES users (id)
);
CREATE TABLE marketplace_listings (
	id INTEGER NOT NULL,
	creator_id INTEGER NOT NULL,
	name VARCHAR(128) NOT NULL,
	slug VARCHAR(128) NOT NULL,
	description TEXT,
	category VARCHAR(64) NOT NULL,
	tags VARCHAR(255),
	price_per_call NUMERIC(20, 8) NOT NULL,
	listing_fee_paid NUMERIC(20, 8) NOT NULL,
	model_key VARCHAR(64),
	pkl_path VARCHAR(512),
	file_size_bytes INTEGER,
	pkl_sha256 VARCHAR(64),
	gcs_uri VARCHAR(512),
	webhook_url VARCHAR(512),
	webhook_secret VARCHAR(256),
	approval_status VARCHAR(20) NOT NULL,
	approval_note TEXT,
	approved_by INTEGER,
	approved_at DATETIME,
	total_revenue NUMERIC(20, 8) NOT NULL,
	creator_revenue NUMERIC(20, 8) NOT NULL,
	protocol_revenue NUMERIC(20, 8) NOT NULL,
	usage_count INTEGER NOT NULL,
	rating_sum FLOAT NOT NULL,
	rating_count INTEGER NOT NULL,
	is_active BOOLEAN NOT NULL,
	is_verified BOOLEAN NOT NULL,
	total_staked NUMERIC(20, 8) NOT NULL,
	staker_count INTEGER NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(creator_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(approved_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE referral_codes (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	code VARCHAR(16) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE referral_uses (
	id INTEGER NOT NULL,
	referrer_id INTEGER NOT NULL,
	referee_id INTEGER NOT NULL,
	bonus_paid BOOLEAN,
	bonus_amount FLOAT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(referrer_id) REFERENCES users (id),
	UNIQUE (referee_id),
	FOREIGN KEY(referee_id) REFERENCES users (id)
);
CREATE TABLE dev_api_keys (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	name VARCHAR(128) NOT NULL,
	key_prefix VARCHAR(12) NOT NULL,
	key_hash VARCHAR(128) NOT NULL,
	key_plain VARCHAR(64),
	"plan" VARCHAR(32) NOT NULL,
	rate_limit_rpm INTEGER NOT NULL,
	rate_limit_rpd INTEGER NOT NULL,
	is_active BOOLEAN NOT NULL,
	last_used_at DATETIME,
	total_requests INTEGER NOT NULL,
	total_vitcoin_billed NUMERIC(20, 8) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	expires_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	UNIQUE (key_hash)
);
CREATE TABLE offer_completions (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	provider VARCHAR(50) NOT NULL,
	reward_type VARCHAR(30) NOT NULL,
	provider_offer_id VARCHAR(128),
	provider_event_id VARCHAR(128),
	status VARCHAR(20) NOT NULL,
	amount NUMERIC(20, 8) NOT NULL,
	currency VARCHAR(10) NOT NULL,
	reward_margin FLOAT NOT NULL,
	wallet_tx_id VARCHAR(36),
	provider_payload JSON NOT NULL,
	provider_payload_hash VARCHAR(128) NOT NULL,
	provider_signature VARCHAR(255),
	event_metadata JSON NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_offer_completions_provider_payload UNIQUE (provider, provider_payload_hash),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE vit_identities (
	id VARCHAR(36) NOT NULL,
	did VARCHAR(255) NOT NULL,
	subject_type VARCHAR(20) NOT NULL,
	user_id INTEGER,
	agent_name VARCHAR(100),
	did_document JSON NOT NULL,
	active BOOLEAN NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE user_vault_positions (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	vault_id INTEGER NOT NULL,
	staked_balance NUMERIC(20, 8) NOT NULL,
	yield_earned NUMERIC(20, 8) NOT NULL,
	entry_roi NUMERIC(10, 4) NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(vault_id) REFERENCES strategy_vaults (id) ON DELETE CASCADE
);
CREATE TABLE social_opportunities (
	id VARCHAR(36) NOT NULL,
	signal_id VARCHAR(36) NOT NULL,
	score FLOAT NOT NULL,
	score_breakdown JSON,
	reasoning TEXT,
	confidence FLOAT,
	priority VARCHAR(20),
	risk_flags JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(signal_id) REFERENCES social_signals (id) ON DELETE CASCADE
);
CREATE TABLE bridge_transactions (
	id INTEGER NOT NULL,
	pool_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	tx_hash VARCHAR(128) NOT NULL,
	direction VARCHAR(16) NOT NULL,
	amount_in NUMERIC(20, 8) NOT NULL,
	amount_out NUMERIC(20, 8) NOT NULL,
	fee NUMERIC(20, 8) NOT NULL,
	exchange_rate NUMERIC(20, 8) NOT NULL,
	destination_address VARCHAR(255) NOT NULL,
	source_address VARCHAR(255),
	status VARCHAR(20) NOT NULL,
	status_message TEXT,
	relayer_tx_hash VARCHAR(128),
	confirmed_at DATETIME,
	completed_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(pool_id) REFERENCES bridge_pools (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE grant_proposals (
	id INTEGER NOT NULL,
	title VARCHAR(255) NOT NULL,
	description TEXT NOT NULL,
	proposer_user_id INTEGER,
	pool_type VARCHAR(20) NOT NULL,
	requested_amount NUMERIC(20, 6) NOT NULL,
	approved_amount NUMERIC(20, 6),
	recipient_user_id INTEGER,
	recipient_address VARCHAR(100),
	status VARCHAR(9) NOT NULL,
	milestones JSON NOT NULL,
	votes_for INTEGER NOT NULL,
	votes_against INTEGER NOT NULL,
	governance_proposal_id INTEGER,
	reviewed_by INTEGER,
	review_notes TEXT,
	created_at DATETIME NOT NULL,
	approved_at DATETIME,
	executed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(proposer_user_id) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(recipient_user_id) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE treasury_deposits (
	id INTEGER NOT NULL,
	pool_type VARCHAR(20) NOT NULL,
	amount NUMERIC(20, 6) NOT NULL,
	source VARCHAR(100) NOT NULL,
	depositor_user_id INTEGER,
	tx_hash VARCHAR(66),
	notes TEXT,
	deposited_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(depositor_user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE inference_proofs (
	id INTEGER NOT NULL,
	model_attestation_id INTEGER NOT NULL,
	attestation_kind VARCHAR(16) NOT NULL,
	input_hash VARCHAR(66) NOT NULL,
	output_hash VARCHAR(66) NOT NULL,
	proof_hash VARCHAR(66) NOT NULL,
	signature TEXT,
	input_summary TEXT,
	output_summary TEXT,
	confidence NUMERIC(5, 4),
	block_number INTEGER NOT NULL,
	anchor_tx VARCHAR(66),
	status VARCHAR(8) NOT NULL,
	verified_by_user_id INTEGER,
	ref_match_id INTEGER,
	ref_prediction_id INTEGER,
	created_at DATETIME NOT NULL,
	anchored_at DATETIME,
	verified_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(model_attestation_id) REFERENCES ai_model_attestations (id) ON DELETE CASCADE,
	UNIQUE (proof_hash),
	FOREIGN KEY(verified_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE community_circles (
	id INTEGER NOT NULL,
	name VARCHAR(100) NOT NULL,
	category VARCHAR(50) NOT NULL,
	creator_id INTEGER NOT NULL,
	member_count INTEGER NOT NULL,
	avg_signal_pct FLOAT NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (name),
	FOREIGN KEY(creator_id) REFERENCES users (id)
);
CREATE TABLE user_iq_test_results (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	score INTEGER NOT NULL,
	total INTEGER NOT NULL,
	iq_score INTEGER NOT NULL,
	label VARCHAR(50) NOT NULL,
	answers JSON NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE sybil_profiles (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	risk_level VARCHAR(7) NOT NULL,
	anomaly_score NUMERIC(5, 4) NOT NULL,
	ip_cluster_id VARCHAR(64),
	device_fingerprints INTEGER NOT NULL,
	account_age_days INTEGER NOT NULL,
	prediction_velocity NUMERIC(8, 4) NOT NULL,
	stake_velocity NUMERIC(8, 4) NOT NULL,
	referral_cluster_score NUMERIC(5, 4) NOT NULL,
	flags TEXT NOT NULL,
	last_evaluated_at DATETIME,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE fraud_alerts (
	id INTEGER NOT NULL,
	user_id INTEGER,
	severity VARCHAR(8) NOT NULL,
	alert_type VARCHAR(100) NOT NULL,
	description TEXT NOT NULL,
	evidence TEXT,
	anomaly_score NUMERIC(5, 4) NOT NULL,
	resolved BOOLEAN NOT NULL,
	resolved_by INTEGER,
	resolution_action VARCHAR(200),
	created_at DATETIME NOT NULL,
	resolved_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(resolved_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE multisig_operations (
	id INTEGER NOT NULL,
	operation_type VARCHAR(100) NOT NULL,
	description TEXT NOT NULL,
	payload TEXT NOT NULL,
	required_signers INTEGER NOT NULL,
	threshold INTEGER NOT NULL,
	status VARCHAR(16) NOT NULL,
	proposer_user_id INTEGER,
	execution_tx VARCHAR(66),
	expires_at DATETIME,
	executed_at DATETIME,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(proposer_user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE rate_limit_ledger (
	id INTEGER NOT NULL,
	user_id INTEGER,
	ip_address VARCHAR(45),
	endpoint VARCHAR(200) NOT NULL,
	call_count INTEGER NOT NULL,
	window_start DATETIME NOT NULL,
	window_end DATETIME NOT NULL,
	blocked BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE kyc_submissions (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	full_name VARCHAR(200) NOT NULL,
	date_of_birth VARCHAR(20) NOT NULL,
	nationality VARCHAR(80) NOT NULL,
	document_type VARCHAR(40) NOT NULL,
	document_number VARCHAR(60) NOT NULL,
	address TEXT,
	status VARCHAR(13) NOT NULL,
	risk_level VARCHAR(6) NOT NULL,
	risk_score INTEGER NOT NULL,
	rule_checks JSON NOT NULL,
	risk_flags JSON NOT NULL,
	reviewed_by INTEGER,
	review_note TEXT,
	rejection_reason VARCHAR(300),
	selfie_data JSON,
	submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	reviewed_at DATETIME,
	approved_at DATETIME,
	expires_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE smart_contracts (
	id INTEGER NOT NULL,
	name VARCHAR(120) NOT NULL,
	symbol VARCHAR(32),
	version VARCHAR(20) NOT NULL,
	address VARCHAR(66) NOT NULL,
	deployer_user_id INTEGER,
	status VARCHAR(10) NOT NULL,
	abi JSON NOT NULL,
	state JSON NOT NULL,
	rules JSON NOT NULL,
	gas_limit INTEGER NOT NULL,
	total_calls INTEGER NOT NULL,
	total_gas_used INTEGER NOT NULL,
	vit_locked NUMERIC(20, 6) NOT NULL,
	description TEXT,
	is_builtin BOOLEAN NOT NULL,
	deployed_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (name),
	UNIQUE (address),
	FOREIGN KEY(deployer_user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE subchain_blocks (
	id INTEGER NOT NULL,
	chain_id INTEGER NOT NULL,
	block_number INTEGER NOT NULL,
	block_hash VARCHAR(66) NOT NULL,
	parent_hash VARCHAR(66) NOT NULL,
	validator_address VARCHAR(66),
	txn_count INTEGER NOT NULL,
	gas_used INTEGER NOT NULL,
	state_root VARCHAR(66) NOT NULL,
	finality_proof TEXT,
	finalized BOOLEAN NOT NULL,
	produced_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (chain_id, block_number),
	FOREIGN KEY(chain_id) REFERENCES sub_chains (id) ON DELETE CASCADE,
	UNIQUE (block_hash)
);
CREATE TABLE cross_chain_messages (
	id INTEGER NOT NULL,
	source_chain_id INTEGER NOT NULL,
	dest_chain_id INTEGER NOT NULL,
	nonce INTEGER NOT NULL,
	message_type VARCHAR(80) NOT NULL,
	payload TEXT NOT NULL,
	payload_hash VARCHAR(66) NOT NULL,
	sender_address VARCHAR(66),
	recipient_address VARCHAR(66),
	status VARCHAR(9) NOT NULL,
	relay_proof TEXT,
	confirmation_block INTEGER,
	fee_paid NUMERIC(20, 6) NOT NULL,
	retry_count INTEGER NOT NULL,
	created_at DATETIME NOT NULL,
	relayed_at DATETIME,
	confirmed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(source_chain_id) REFERENCES sub_chains (id) ON DELETE CASCADE,
	FOREIGN KEY(dest_chain_id) REFERENCES sub_chains (id) ON DELETE CASCADE
);
CREATE TABLE subchain_validators (
	id INTEGER NOT NULL,
	chain_id INTEGER NOT NULL,
	validator_user_id INTEGER NOT NULL,
	stake NUMERIC(20, 6) NOT NULL,
	blocks_produced INTEGER NOT NULL,
	uptime_pct NUMERIC(5, 2) NOT NULL,
	is_active BOOLEAN NOT NULL,
	joined_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (chain_id, validator_user_id),
	FOREIGN KEY(chain_id) REFERENCES sub_chains (id) ON DELETE CASCADE,
	FOREIGN KEY(validator_user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE ai_agent_registrations (
	id INTEGER NOT NULL,
	agent_id VARCHAR(100) NOT NULL,
	name VARCHAR(200) NOT NULL,
	description TEXT,
	owner_user_id INTEGER,
	status VARCHAR(9) NOT NULL,
	capabilities TEXT NOT NULL,
	did_identifier VARCHAR(200),
	public_key TEXT,
	endpoint_url VARCHAR(500),
	stake_amount NUMERIC(20, 6) NOT NULL,
	reputation_score NUMERIC(8, 4) NOT NULL,
	accuracy_rate NUMERIC(5, 4) NOT NULL,
	total_tasks INTEGER NOT NULL,
	successful_tasks INTEGER NOT NULL,
	failed_tasks INTEGER NOT NULL,
	total_earned_vit NUMERIC(20, 6) NOT NULL,
	total_slashed_vit NUMERIC(20, 6) NOT NULL,
	version VARCHAR(30) NOT NULL,
	is_builtin BOOLEAN NOT NULL,
	registered_at DATETIME NOT NULL,
	last_active_at DATETIME,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (agent_id),
	FOREIGN KEY(owner_user_id) REFERENCES users (id) ON DELETE SET NULL,
	UNIQUE (did_identifier)
);
CREATE TABLE user_prophecy_progress (
	id INTEGER NOT NULL,
	user_id INTEGER,
	current_chapter_id INTEGER,
	chapters_completed JSON,
	chapters_claimed JSON,
	total_qualified_predictions INTEGER,
	total_qualified_wins INTEGER,
	current_accuracy FLOAT,
	last_evaluated_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(current_chapter_id) REFERENCES prophecy_chapters (id)
);
CREATE TABLE module_training_jobs (
	id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	status VARCHAR(20) NOT NULL,
	league VARCHAR(100) NOT NULL,
	team_filter VARCHAR(200),
	date_from DATE,
	date_to DATE,
	row_count INTEGER,
	column_profile JSON,
	quality_score NUMERIC(5, 2),
	quality_breakdown JSON,
	generated_prompt TEXT,
	vitcoin_reward NUMERIC(20, 8) NOT NULL,
	vitcoin_earned BOOLEAN NOT NULL,
	model_accuracy NUMERIC(5, 2),
	improvement_suggestion TEXT,
	submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	completed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE predictions (
	id INTEGER NOT NULL,
	match_id INTEGER,
	market_id VARCHAR(36),
	user_id INTEGER,
	request_hash VARCHAR,
	home_prob FLOAT NOT NULL,
	draw_prob FLOAT NOT NULL,
	away_prob FLOAT NOT NULL,
	over_25_prob FLOAT,
	under_25_prob FLOAT,
	btts_prob FLOAT,
	no_btts_prob FLOAT,
	ah_line FLOAT,
	ah_home_prob FLOAT,
	ah_away_prob FLOAT,
	ah_lines JSON,
	cs_probs JSON,
	top_correct_score VARCHAR(8),
	top_cs_prob FLOAT,
	model_consensus JSON,
	alternative_bets JSON,
	status VARCHAR(32) DEFAULT 'READY' NOT NULL,
	source VARCHAR(32) DEFAULT 'live_generated' NOT NULL,
	is_seed BOOLEAN DEFAULT 'false' NOT NULL,
	provenance JSON,
	job_id VARCHAR(64),
	error_message VARCHAR,
	consensus_prob FLOAT,
	final_ev FLOAT,
	recommended_stake FLOAT,
	model_weights JSON,
	model_insights JSON,
	confidence FLOAT,
	bet_side VARCHAR,
	entry_odds FLOAT,
	raw_edge FLOAT,
	normalized_edge FLOAT,
	vig_free_edge FLOAT,
	submitted_market_id VARCHAR,
	submitted_market_side VARCHAR,
	submitted_stake FLOAT,
	was_correct BOOLEAN,
	settled_profit FLOAT,
	timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT check_home_prob CHECK (home_prob >= 0 AND home_prob <= 1),
	CONSTRAINT check_draw_prob CHECK (draw_prob >= 0 AND draw_prob <= 1),
	CONSTRAINT check_away_prob CHECK (away_prob >= 0 AND away_prob <= 1),
	CONSTRAINT check_stake_limit CHECK (recommended_stake >= 0 AND recommended_stake <= 0.20),
	FOREIGN KEY(match_id) REFERENCES matches (id),
	FOREIGN KEY(market_id) REFERENCES markets (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE ai_predictions (
	id INTEGER NOT NULL,
	match_id INTEGER NOT NULL,
	source VARCHAR(50) NOT NULL,
	home_prob FLOAT NOT NULL,
	draw_prob FLOAT NOT NULL,
	away_prob FLOAT NOT NULL,
	confidence FLOAT,
	reason VARCHAR(500),
	raw_content TEXT,
	submitted_by INTEGER,
	model_version VARCHAR(50),
	is_certified BOOLEAN,
	timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
	was_correct BOOLEAN,
	calibration_error FLOAT,
	PRIMARY KEY (id),
	FOREIGN KEY(match_id) REFERENCES matches (id),
	FOREIGN KEY(submitted_by) REFERENCES users (id)
);
CREATE TABLE ai_signal_cache (
	id INTEGER NOT NULL,
	match_id INTEGER NOT NULL,
	consensus_home FLOAT NOT NULL,
	consensus_draw FLOAT NOT NULL,
	consensus_away FLOAT NOT NULL,
	disagreement_score FLOAT NOT NULL,
	max_confidence FLOAT NOT NULL,
	weighted_home FLOAT NOT NULL,
	weighted_draw FLOAT NOT NULL,
	weighted_away FLOAT NOT NULL,
	per_ai_predictions JSON,
	timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	UNIQUE (match_id),
	FOREIGN KEY(match_id) REFERENCES matches (id)
);
CREATE TABLE iot_events (
	id INTEGER NOT NULL,
	source VARCHAR(50) NOT NULL,
	event_type VARCHAR(50) NOT NULL,
	match_id INTEGER,
	payload JSON NOT NULL,
	processed BOOLEAN,
	processed_at DATETIME,
	agent_response TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(match_id) REFERENCES matches (id) ON DELETE SET NULL
);
CREATE TABLE agent_insights (
	id INTEGER NOT NULL,
	agent_name VARCHAR(50) NOT NULL,
	insight_type VARCHAR(50) NOT NULL,
	match_id INTEGER,
	team VARCHAR(100),
	ai_provider VARCHAR(20) NOT NULL,
	content TEXT NOT NULL,
	meta JSON NOT NULL,
	confidence FLOAT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(match_id) REFERENCES matches (id) ON DELETE SET NULL
);
CREATE TABLE wallet_profiles (
	id VARCHAR(36) NOT NULL,
	wallet_id VARCHAR(36) NOT NULL,
	vit_balance NUMERIC(20, 8) NOT NULL,
	risk_score FLOAT NOT NULL,
	activity_score FLOAT NOT NULL,
	trading_style VARCHAR(20) NOT NULL,
	total_trades INTEGER NOT NULL,
	total_trade_volume NUMERIC(20, 8) NOT NULL,
	avg_trade_size NUMERIC(20, 8) NOT NULL,
	avg_holding_duration_seconds FLOAT NOT NULL,
	holding_duration_count INTEGER NOT NULL,
	volatility_exposure FLOAT NOT NULL,
	last_trade_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (wallet_id),
	FOREIGN KEY(wallet_id) REFERENCES wallets (id) ON DELETE CASCADE
);
CREATE TABLE wallet_transactions (
	id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	wallet_id VARCHAR(36) NOT NULL,
	type VARCHAR(20) NOT NULL,
	currency VARCHAR(10) NOT NULL,
	amount NUMERIC(20, 8) NOT NULL,
	direction VARCHAR(10) NOT NULL,
	status VARCHAR(20) NOT NULL,
	reference VARCHAR(255),
	description VARCHAR(500),
	rate_snapshot JSON,
	fee_amount NUMERIC(20, 8) NOT NULL,
	fee_currency VARCHAR(10),
	tx_metadata JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	processed_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_wallet_transactions_reference UNIQUE (reference),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(wallet_id) REFERENCES wallets (id) ON DELETE CASCADE
);
CREATE TABLE withdrawal_requests (
	id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	wallet_id VARCHAR(36) NOT NULL,
	currency VARCHAR(10) NOT NULL,
	amount NUMERIC(20, 8) NOT NULL,
	fee_amount NUMERIC(20, 8) NOT NULL,
	net_amount NUMERIC(20, 8) NOT NULL,
	destination VARCHAR(255) NOT NULL,
	destination_type VARCHAR(30) NOT NULL,
	bank_code VARCHAR(20),
	account_number VARCHAR(30),
	account_name VARCHAR(120),
	status VARCHAR(30) NOT NULL,
	auto_approved BOOLEAN NOT NULL,
	reviewed_by INTEGER,
	review_note TEXT,
	requested_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	processed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(wallet_id) REFERENCES wallets (id) ON DELETE CASCADE,
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
);
CREATE TABLE savings_vaults (
	id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	wallet_id VARCHAR(36) NOT NULL,
	name VARCHAR(100) NOT NULL,
	vault_type VARCHAR(30) NOT NULL,
	currency VARCHAR(10) NOT NULL,
	current_balance NUMERIC(20, 8) NOT NULL,
	target_amount NUMERIC(20, 8),
	lock_period_days INTEGER NOT NULL,
	apy_pct NUMERIC(6, 4) NOT NULL,
	is_active BOOLEAN NOT NULL,
	locked_until DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(wallet_id) REFERENCES wallets (id) ON DELETE CASCADE
);
CREATE TABLE p2p_offers (
	id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	wallet_id VARCHAR(36) NOT NULL,
	offer_type VARCHAR(10) NOT NULL,
	currency VARCHAR(10) NOT NULL,
	total_amount NUMERIC(20, 8) NOT NULL,
	available_amount NUMERIC(20, 8) NOT NULL,
	escrowed_amount NUMERIC(20, 8) NOT NULL,
	rate_ngn NUMERIC(20, 8) NOT NULL,
	min_order NUMERIC(20, 8) NOT NULL,
	max_order NUMERIC(20, 8) NOT NULL,
	payment_method VARCHAR(100) NOT NULL,
	payment_details JSON,
	status VARCHAR(20) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(wallet_id) REFERENCES wallets (id) ON DELETE CASCADE
);
CREATE TABLE identity_teams (
	id INTEGER NOT NULL,
	organization_id INTEGER NOT NULL,
	name VARCHAR(150) NOT NULL,
	slug VARCHAR(100) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(organization_id) REFERENCES identity_organizations (id) ON DELETE CASCADE
);
CREATE TABLE identity_organization_members (
	id INTEGER NOT NULL,
	organization_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	role_in_org VARCHAR(50) NOT NULL,
	joined_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_org_member_org_user UNIQUE (organization_id, user_id),
	FOREIGN KEY(organization_id) REFERENCES identity_organizations (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE user_task_completions (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	user_id INTEGER NOT NULL,
	task_id INTEGER NOT NULL,
	current_progress INTEGER NOT NULL,
	required_progress INTEGER NOT NULL,
	is_completed BOOLEAN NOT NULL,
	completed_count INTEGER NOT NULL,
	last_completed_at DATETIME,
	next_reset_at DATETIME,
	total_vit_earned NUMERIC(20, 8) NOT NULL,
	total_xp_earned INTEGER NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME NOT NULL,
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(task_id) REFERENCES tasks (id)
);
CREATE TABLE slash_appeals (
	id INTEGER NOT NULL,
	slash_event_id INTEGER NOT NULL,
	validator_address VARCHAR(255) NOT NULL,
	justification TEXT NOT NULL,
	status VARCHAR(16) NOT NULL,
	reviewed_at DATETIME,
	reviewer_notes TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(slash_event_id) REFERENCES slash_events (id)
);
CREATE TABLE core_balances (
	id VARCHAR(36) NOT NULL,
	wallet_id VARCHAR(36) NOT NULL,
	asset_symbol VARCHAR(20) NOT NULL,
	confirmed_balance NUMERIC(36, 18) NOT NULL,
	pending_balance NUMERIC(36, 18) NOT NULL,
	reserved_balance NUMERIC(36, 18) NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_wallet_asset_balance UNIQUE (wallet_id, asset_symbol),
	FOREIGN KEY(wallet_id) REFERENCES core_wallets (id) ON DELETE CASCADE,
	FOREIGN KEY(asset_symbol) REFERENCES core_assets (symbol)
);
CREATE TABLE core_addresses (
	id VARCHAR(36) NOT NULL,
	wallet_id VARCHAR(36) NOT NULL,
	network VARCHAR(50) NOT NULL,
	address VARCHAR(128) NOT NULL,
	derivation_path VARCHAR(100),
	is_active BOOLEAN NOT NULL,
	metadata_json JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_network_address UNIQUE (network, address),
	FOREIGN KEY(wallet_id) REFERENCES core_wallets (id) ON DELETE CASCADE
);
CREATE TABLE storage_proofs (
	id INTEGER NOT NULL,
	content_id INTEGER NOT NULL,
	prover_user_id INTEGER,
	node_address VARCHAR(200) NOT NULL,
	proof_type VARCHAR(60) NOT NULL,
	proof_data TEXT NOT NULL,
	proof_hash VARCHAR(66) NOT NULL,
	status VARCHAR(10) NOT NULL,
	stake_locked NUMERIC(20, 6) NOT NULL,
	reward_earned NUMERIC(20, 6) NOT NULL,
	submitted_at DATETIME NOT NULL,
	verified_at DATETIME,
	expires_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(content_id) REFERENCES content_hash_registry (id) ON DELETE CASCADE,
	FOREIGN KEY(prover_user_id) REFERENCES users (id) ON DELETE SET NULL,
	UNIQUE (proof_hash)
);
CREATE TABLE data_availability_attestations (
	id INTEGER NOT NULL,
	content_id INTEGER NOT NULL,
	attestor_user_id INTEGER NOT NULL,
	available BOOLEAN NOT NULL,
	latency_ms INTEGER,
	signature VARCHAR(200) NOT NULL,
	attested_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (content_id, attestor_user_id),
	FOREIGN KEY(content_id) REFERENCES content_hash_registry (id) ON DELETE CASCADE,
	FOREIGN KEY(attestor_user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE validator_predictions (
	id VARCHAR(36) NOT NULL,
	validator_id VARCHAR(36) NOT NULL,
	match_id VARCHAR(100) NOT NULL,
	p_home NUMERIC(5, 4) NOT NULL,
	p_draw NUMERIC(5, 4) NOT NULL,
	p_away NUMERIC(5, 4) NOT NULL,
	outcomes JSON,
	category VARCHAR(50) NOT NULL,
	confidence NUMERIC(5, 4) NOT NULL,
	submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	result VARCHAR(20) NOT NULL,
	trust_delta NUMERIC(6, 4),
	reward_earned NUMERIC(20, 8) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_validator_match_prediction UNIQUE (validator_id, match_id),
	FOREIGN KEY(validator_id) REFERENCES validator_profiles (id) ON DELETE CASCADE
);
CREATE TABLE match_settlements (
	id VARCHAR(36) NOT NULL,
	market_id VARCHAR(36),
	match_id VARCHAR(100) NOT NULL,
	consensus_id VARCHAR(36) NOT NULL,
	oracle_result VARCHAR(10) NOT NULL,
	total_pool NUMERIC(20, 8) NOT NULL,
	winning_pool NUMERIC(20, 8) NOT NULL,
	validator_fund NUMERIC(20, 8) NOT NULL,
	treasury_fund NUMERIC(20, 8) NOT NULL,
	burn_amount NUMERIC(20, 8) NOT NULL,
	ai_fund NUMERIC(20, 8) NOT NULL,
	settled_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (market_id),
	FOREIGN KEY(market_id) REFERENCES markets (id),
	UNIQUE (match_id),
	FOREIGN KEY(consensus_id) REFERENCES consensus_predictions (id)
);
CREATE TABLE validator_slash_events (
	id VARCHAR(36) NOT NULL,
	validator_id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	slash_reason VARCHAR(200) NOT NULL,
	slash_pct NUMERIC(5, 4) NOT NULL,
	slash_amount NUMERIC(20, 8) NOT NULL,
	stake_before NUMERIC(20, 8) NOT NULL,
	stake_after NUMERIC(20, 8) NOT NULL,
	trust_score_at_slash NUMERIC(5, 4) NOT NULL,
	prior_slash_count INTEGER NOT NULL,
	admin_user_id INTEGER,
	slashed_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(validator_id) REFERENCES validator_profiles (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE gov_votes (
	id INTEGER NOT NULL,
	proposal_id INTEGER NOT NULL,
	voter_id INTEGER NOT NULL,
	choice VARCHAR(10) NOT NULL,
	voting_power FLOAT NOT NULL,
	reason TEXT,
	voted_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_gov_vote_proposal_voter UNIQUE (proposal_id, voter_id),
	FOREIGN KEY(proposal_id) REFERENCES gov_proposals (id) ON DELETE CASCADE,
	FOREIGN KEY(voter_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE evidence_snapshots (
	id INTEGER NOT NULL,
	match_id INTEGER NOT NULL,
	feature_completeness_pct INTEGER NOT NULL,
	provider_data JSON NOT NULL,
	quality_score INTEGER NOT NULL,
	missing_critical_inputs JSON NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(match_id) REFERENCES matches (id) ON DELETE CASCADE
);
CREATE TABLE market_mappings (
	id INTEGER NOT NULL,
	match_id INTEGER,
	internal_market_id VARCHAR(36),
	provider_name VARCHAR(50) NOT NULL,
	external_match_id VARCHAR(100),
	external_selection_id VARCHAR(100),
	market_type VARCHAR(50),
	selection_name VARCHAR(50),
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(match_id) REFERENCES matches (id),
	FOREIGN KEY(internal_market_id) REFERENCES markets (id)
);
CREATE TABLE affiliate_clicks (
	id INTEGER NOT NULL,
	user_id INTEGER,
	match_id INTEGER,
	provider_name VARCHAR(50),
	market_type VARCHAR(50),
	selection_name VARCHAR(50),
	utm_source VARCHAR(100),
	utm_medium VARCHAR(100),
	utm_campaign VARCHAR(100),
	utm_content VARCHAR(100),
	ip_address VARCHAR(45),
	user_agent VARCHAR(255),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(match_id) REFERENCES matches (id)
);
CREATE TABLE merit_events (
	id INTEGER NOT NULL,
	merit_score_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	event_type VARCHAR(20) NOT NULL,
	points_delta NUMERIC(16, 4) NOT NULL,
	score_before NUMERIC(16, 4) NOT NULL,
	score_after NUMERIC(16, 4) NOT NULL,
	tier_before VARCHAR(9) NOT NULL,
	tier_after VARCHAR(9) NOT NULL,
	bonus_vit NUMERIC(20, 6) NOT NULL,
	ref_id VARCHAR(100),
	description TEXT,
	occurred_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(merit_score_id) REFERENCES merit_scores (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE watchlist_items (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	match_id INTEGER NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(match_id) REFERENCES matches (id) ON DELETE CASCADE
);
CREATE TABLE election_predictions (
	id VARCHAR(36) NOT NULL,
	election_id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	candidate_id VARCHAR(36),
	predicted_outcome JSON NOT NULL,
	reasoning TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(election_id) REFERENCES elections (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(candidate_id) REFERENCES candidates (id) ON DELETE SET NULL
);
CREATE TABLE academic_resources (
	id INTEGER NOT NULL,
	course_id INTEGER NOT NULL,
	title VARCHAR(255) NOT NULL,
	description TEXT,
	resource_type VARCHAR(32) NOT NULL,
	file_url VARCHAR(512) NOT NULL,
	file_size_bytes INTEGER,
	university VARCHAR(255),
	faculty VARCHAR(255),
	department VARCHAR(255),
	academic_year INTEGER,
	semester INTEGER,
	upvotes INTEGER,
	downloads INTEGER,
	is_verified BOOLEAN,
	vit_reward_paid BOOLEAN,
	content_summary TEXT,
	uploaded_by INTEGER NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(course_id) REFERENCES academic_courses (id),
	FOREIGN KEY(uploaded_by) REFERENCES users (id)
);
CREATE TABLE campus_comments (
	id INTEGER NOT NULL,
	post_id INTEGER NOT NULL,
	author_id INTEGER NOT NULL,
	content TEXT NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(post_id) REFERENCES campus_posts (id),
	FOREIGN KEY(author_id) REFERENCES users (id)
);
CREATE TABLE marketplace_usage_logs (
	id INTEGER NOT NULL,
	listing_id INTEGER NOT NULL,
	caller_id INTEGER NOT NULL,
	vitcoin_charged NUMERIC(20, 8) NOT NULL,
	creator_share NUMERIC(20, 8) NOT NULL,
	protocol_share NUMERIC(20, 8) NOT NULL,
	input_summary TEXT,
	output_summary TEXT,
	status VARCHAR(20) NOT NULL,
	error_message TEXT,
	called_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(listing_id) REFERENCES marketplace_listings (id) ON DELETE CASCADE,
	FOREIGN KEY(caller_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE marketplace_ratings (
	id INTEGER NOT NULL,
	listing_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	stars INTEGER NOT NULL,
	review TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_rating_listing_user UNIQUE (listing_id, user_id),
	FOREIGN KEY(listing_id) REFERENCES marketplace_listings (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE marketplace_stakes (
	id INTEGER NOT NULL,
	listing_id INTEGER NOT NULL,
	staker_id INTEGER NOT NULL,
	amount NUMERIC(20, 8) NOT NULL,
	current_amount NUMERIC(20, 8) NOT NULL,
	slashed_amount NUMERIC(20, 8) NOT NULL,
	earnings_accumulated NUMERIC(20, 8) NOT NULL,
	lock_period_days INTEGER NOT NULL,
	staked_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	unlock_at DATETIME,
	status VARCHAR(20) NOT NULL,
	withdrawn_at DATETIME,
	last_earnings_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_stake_listing_staker UNIQUE (listing_id, staker_id),
	FOREIGN KEY(listing_id) REFERENCES marketplace_listings (id) ON DELETE CASCADE,
	FOREIGN KEY(staker_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE marketplace_slash_events (
	id INTEGER NOT NULL,
	listing_id INTEGER NOT NULL,
	triggered_by INTEGER,
	reason VARCHAR(64) NOT NULL,
	slash_pct FLOAT NOT NULL,
	total_slashed NUMERIC(20, 8) NOT NULL,
	stakers_affected INTEGER NOT NULL,
	note TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(listing_id) REFERENCES marketplace_listings (id) ON DELETE CASCADE,
	FOREIGN KEY(triggered_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE dev_api_usage_logs (
	id INTEGER NOT NULL,
	api_key_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	endpoint VARCHAR(255) NOT NULL,
	method VARCHAR(8) NOT NULL,
	status_code INTEGER NOT NULL,
	latency_ms INTEGER,
	vitcoin_billed NUMERIC(20, 8) NOT NULL,
	ip_address VARCHAR(45),
	user_agent VARCHAR(255),
	called_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(api_key_id) REFERENCES dev_api_keys (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE postback_audit_logs (
	id INTEGER NOT NULL,
	offer_completion_id INTEGER,
	provider VARCHAR(50) NOT NULL,
	received_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	ip_address VARCHAR(45),
	headers JSON NOT NULL,
	payload JSON NOT NULL,
	payload_hash VARCHAR(128) NOT NULL,
	signature VARCHAR(255),
	validation_status VARCHAR(30) NOT NULL,
	validation_details JSON NOT NULL,
	error_message VARCHAR(500),
	PRIMARY KEY (id),
	FOREIGN KEY(offer_completion_id) REFERENCES offer_completions (id) ON DELETE CASCADE
);
CREATE TABLE verifiable_credentials (
	id VARCHAR(36) NOT NULL,
	identity_id VARCHAR(36) NOT NULL,
	credential_type VARCHAR(50) NOT NULL,
	issuer VARCHAR(255) NOT NULL,
	credential JSON NOT NULL,
	issued_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	expires_at DATETIME,
	revoked BOOLEAN NOT NULL,
	revoked_at DATETIME,
	revocation_reason TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY(identity_id) REFERENCES vit_identities (id) ON DELETE CASCADE
);
CREATE TABLE social_candidates (
	id VARCHAR(36) NOT NULL,
	opportunity_id VARCHAR(36) NOT NULL,
	generated_content TEXT NOT NULL,
	content_format VARCHAR(50),
	provenance JSON,
	risk_flags JSON,
	state VARCHAR(50) NOT NULL,
	review_history JSON,
	created_by VARCHAR(100),
	reviewed_by VARCHAR(100),
	reviewed_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(opportunity_id) REFERENCES social_opportunities (id) ON DELETE CASCADE
);
CREATE TABLE bridge_audit_logs (
	id INTEGER NOT NULL,
	transaction_id INTEGER NOT NULL,
	event VARCHAR(64) NOT NULL,
	actor VARCHAR(32) NOT NULL,
	detail TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(transaction_id) REFERENCES bridge_transactions (id) ON DELETE CASCADE
);
CREATE TABLE treasury_allocations (
	id INTEGER NOT NULL,
	pool_id INTEGER NOT NULL,
	grant_id INTEGER,
	recipient_user_id INTEGER,
	amount NUMERIC(20, 6) NOT NULL,
	reason VARCHAR(255) NOT NULL,
	status VARCHAR(11) NOT NULL,
	tx_hash VARCHAR(66),
	scheduled_at DATETIME,
	released_at DATETIME,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(pool_id) REFERENCES treasury_pools (id) ON DELETE CASCADE,
	FOREIGN KEY(grant_id) REFERENCES grant_proposals (id) ON DELETE SET NULL,
	FOREIGN KEY(recipient_user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE verification_disputes (
	id INTEGER NOT NULL,
	proof_id INTEGER NOT NULL,
	challenger_user_id INTEGER,
	reason TEXT NOT NULL,
	evidence_hash VARCHAR(66),
	resolved BOOLEAN NOT NULL,
	upheld BOOLEAN,
	resolver_user_id INTEGER,
	resolution_notes TEXT,
	stake_slashed NUMERIC(20, 6) NOT NULL,
	created_at DATETIME NOT NULL,
	resolved_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(proof_id) REFERENCES inference_proofs (id) ON DELETE CASCADE,
	FOREIGN KEY(challenger_user_id) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(resolver_user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE community_members (
	id INTEGER NOT NULL,
	circle_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	joined_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(circle_id) REFERENCES community_circles (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE TABLE multisig_signatures (
	id INTEGER NOT NULL,
	operation_id INTEGER NOT NULL,
	signer_user_id INTEGER NOT NULL,
	signature_hash VARCHAR(66) NOT NULL,
	approved BOOLEAN NOT NULL,
	signed_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (operation_id, signer_user_id),
	FOREIGN KEY(operation_id) REFERENCES multisig_operations (id) ON DELETE CASCADE,
	FOREIGN KEY(signer_user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE wallet_freezes (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	status VARCHAR(9) NOT NULL,
	reason TEXT NOT NULL,
	freeze_type VARCHAR(60) NOT NULL,
	frozen_amount NUMERIC(20, 6),
	fraud_alert_id INTEGER,
	frozen_by INTEGER,
	lifted_by INTEGER,
	lift_notes TEXT,
	auto_lift_at DATETIME,
	frozen_at DATETIME NOT NULL,
	lifted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(fraud_alert_id) REFERENCES fraud_alerts (id) ON DELETE SET NULL,
	FOREIGN KEY(frozen_by) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(lifted_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE kyc_audit_events (
	id INTEGER NOT NULL,
	submission_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	actor_id INTEGER,
	event_type VARCHAR(60) NOT NULL,
	from_status VARCHAR(30),
	to_status VARCHAR(30) NOT NULL,
	note TEXT,
	event_data JSON NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(submission_id) REFERENCES kyc_submissions (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE contract_calls (
	id INTEGER NOT NULL,
	contract_id INTEGER NOT NULL,
	caller_user_id INTEGER,
	method VARCHAR(120) NOT NULL,
	params JSON NOT NULL,
	result JSON,
	status VARCHAR(10) NOT NULL,
	gas_used INTEGER NOT NULL,
	error_message TEXT,
	tx_hash VARCHAR(66) NOT NULL,
	block_number INTEGER NOT NULL,
	called_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(contract_id) REFERENCES smart_contracts (id) ON DELETE CASCADE,
	FOREIGN KEY(caller_user_id) REFERENCES users (id) ON DELETE SET NULL,
	UNIQUE (tx_hash)
);
CREATE TABLE contract_upgrades (
	id INTEGER NOT NULL,
	contract_id INTEGER NOT NULL,
	from_version VARCHAR(20) NOT NULL,
	to_version VARCHAR(20) NOT NULL,
	proposed_by INTEGER,
	governance_proposal_id INTEGER,
	new_abi JSON NOT NULL,
	new_rules JSON NOT NULL,
	migration_notes TEXT,
	approved BOOLEAN NOT NULL,
	executed BOOLEAN NOT NULL,
	proposed_at DATETIME NOT NULL,
	executed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(contract_id) REFERENCES smart_contracts (id) ON DELETE CASCADE,
	FOREIGN KEY(proposed_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE agent_performance_records (
	id INTEGER NOT NULL,
	agent_id INTEGER NOT NULL,
	task_type VARCHAR(100) NOT NULL,
	task_ref VARCHAR(100),
	success BOOLEAN NOT NULL,
	latency_ms INTEGER,
	accuracy NUMERIC(5, 4),
	vit_earned NUMERIC(20, 6) NOT NULL,
	proof_hash VARCHAR(66),
	notes TEXT,
	recorded_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(agent_id) REFERENCES ai_agent_registrations (id) ON DELETE CASCADE
);
CREATE TABLE agent_credentials (
	id INTEGER NOT NULL,
	agent_id INTEGER NOT NULL,
	credential_type VARCHAR(100) NOT NULL,
	credential_hash VARCHAR(66) NOT NULL,
	issued_by VARCHAR(200),
	status VARCHAR(7) NOT NULL,
	issued_at DATETIME NOT NULL,
	expires_at DATETIME,
	revoked_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(agent_id) REFERENCES ai_agent_registrations (id) ON DELETE CASCADE
);
CREATE TABLE agent_payment_routes (
	id INTEGER NOT NULL,
	agent_id INTEGER NOT NULL,
	route_type VARCHAR(60) NOT NULL,
	recipient_address VARCHAR(200) NOT NULL,
	split_pct NUMERIC(5, 2) NOT NULL,
	is_active BOOLEAN NOT NULL,
	total_routed NUMERIC(20, 6) NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (agent_id, route_type),
	FOREIGN KEY(agent_id) REFERENCES ai_agent_registrations (id) ON DELETE CASCADE
);
CREATE TABLE module_training_guide_steps (
	id VARCHAR(36) NOT NULL,
	job_id VARCHAR(36) NOT NULL,
	step_number INTEGER NOT NULL,
	title VARCHAR(200) NOT NULL,
	description TEXT NOT NULL,
	required_columns JSON,
	example_data JSON,
	tips JSON,
	is_active BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(job_id) REFERENCES module_training_jobs (id) ON DELETE CASCADE
);
CREATE TABLE clv_entries (
	id INTEGER NOT NULL,
	match_id INTEGER,
	prediction_id INTEGER,
	bet_side VARCHAR NOT NULL,
	entry_odds FLOAT NOT NULL,
	closing_odds FLOAT,
	clv FLOAT,
	bet_outcome VARCHAR,
	profit FLOAT,
	timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(match_id) REFERENCES matches (id),
	FOREIGN KEY(prediction_id) REFERENCES predictions (id)
);
CREATE TABLE wallet_user_subscriptions (
	id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	plan_id VARCHAR(36) NOT NULL,
	currency_paid VARCHAR(10) NOT NULL,
	amount_paid NUMERIC(10, 2) NOT NULL,
	started_at DATETIME NOT NULL,
	expires_at DATETIME NOT NULL,
	auto_renew BOOLEAN NOT NULL,
	status VARCHAR(20) NOT NULL,
	renewal_tx_id VARCHAR(36),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(plan_id) REFERENCES wallet_subscription_plans (id),
	FOREIGN KEY(renewal_tx_id) REFERENCES wallet_transactions (id)
);
CREATE TABLE p2p_orders (
	id VARCHAR(36) NOT NULL,
	offer_id VARCHAR(36) NOT NULL,
	buyer_id INTEGER NOT NULL,
	seller_id INTEGER NOT NULL,
	amount NUMERIC(20, 8) NOT NULL,
	rate_ngn NUMERIC(20, 8) NOT NULL,
	fiat_total_ngn NUMERIC(20, 8) NOT NULL,
	escrow_tx_id VARCHAR(36),
	release_tx_id VARCHAR(36),
	status VARCHAR(30) NOT NULL,
	dispute_reason TEXT,
	admin_note TEXT,
	payment_confirmed_at DATETIME,
	completed_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(offer_id) REFERENCES p2p_offers (id) ON DELETE CASCADE,
	FOREIGN KEY(buyer_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(seller_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(escrow_tx_id) REFERENCES wallet_transactions (id),
	FOREIGN KEY(release_tx_id) REFERENCES wallet_transactions (id)
);
CREATE TABLE identity_team_members (
	id INTEGER NOT NULL,
	team_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	role_in_team VARCHAR(50) NOT NULL,
	joined_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_team_member_team_user UNIQUE (team_id, user_id),
	FOREIGN KEY(team_id) REFERENCES identity_teams (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE rollover_certificates (
	id INTEGER NOT NULL,
	fixture_id INTEGER NOT NULL,
	prediction_id INTEGER,
	pipeline_run_id VARCHAR(36),
	outcome VARCHAR(20) NOT NULL,
	outcome_label VARCHAR(60),
	signal_density FLOAT NOT NULL,
	model_confidence FLOAT,
	simulation_agreement FLOAT,
	mc_home_prob FLOAT,
	mc_draw_prob FLOAT,
	mc_away_prob FLOAT,
	mc_btts_prob FLOAT,
	mc_over25_prob FLOAT,
	mc_under25_prob FLOAT,
	mc_over35_prob FLOAT,
	home_lambda FLOAT,
	away_lambda FLOAT,
	simulations_run INTEGER,
	top_correct_scores JSON,
	home_xg FLOAT,
	away_xg FLOAT,
	xg_source VARCHAR(20),
	kelly_fraction FLOAT,
	status VARCHAR(20) NOT NULL,
	conflict_flags JSON,
	settled_correct BOOLEAN,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(fixture_id) REFERENCES matches (id),
	FOREIGN KEY(prediction_id) REFERENCES predictions (id)
);
CREATE TABLE storage_challenges (
	id INTEGER NOT NULL,
	proof_id INTEGER NOT NULL,
	challenger_user_id INTEGER,
	challenge_nonce VARCHAR(66) NOT NULL,
	expected_response_hash VARCHAR(66) NOT NULL,
	actual_response_hash VARCHAR(66),
	status VARCHAR(16) NOT NULL,
	slash_amount NUMERIC(20, 6) NOT NULL,
	response_deadline DATETIME NOT NULL,
	issued_at DATETIME NOT NULL,
	responded_at DATETIME,
	resolved_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (proof_id),
	FOREIGN KEY(proof_id) REFERENCES storage_proofs (id) ON DELETE CASCADE,
	FOREIGN KEY(challenger_user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE TABLE validator_appeals (
	id VARCHAR(36) NOT NULL,
	validator_id VARCHAR(36) NOT NULL,
	user_id INTEGER NOT NULL,
	slash_event_id VARCHAR(36),
	reason TEXT NOT NULL,
	evidence_url VARCHAR(512),
	status VARCHAR(20) NOT NULL,
	admin_note TEXT,
	reviewed_by INTEGER,
	restake_amount NUMERIC(20, 8) NOT NULL,
	submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	reviewed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(validator_id) REFERENCES validator_profiles (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	FOREIGN KEY(slash_event_id) REFERENCES validator_slash_events (id) ON DELETE SET NULL,
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
);
CREATE TABLE market_requirement_results (
	id INTEGER NOT NULL,
	evidence_snapshot_id INTEGER NOT NULL,
	market_key VARCHAR(50) NOT NULL,
	requirements_met BOOLEAN NOT NULL,
	reason TEXT,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(evidence_snapshot_id) REFERENCES evidence_snapshots (id) ON DELETE CASCADE
);
CREATE TABLE social_publication_records (
	id VARCHAR(36) NOT NULL,
	candidate_id VARCHAR(36) NOT NULL,
	platform VARCHAR(50) NOT NULL,
	status VARCHAR(50) NOT NULL,
	external_ref VARCHAR(255),
	url VARCHAR(500),
	error_message TEXT,
	published_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_candidate_platform_publication UNIQUE (candidate_id, platform),
	FOREIGN KEY(candidate_id) REFERENCES social_candidates (id) ON DELETE CASCADE
);
CREATE TABLE contract_events (
	id INTEGER NOT NULL,
	contract_id INTEGER NOT NULL,
	call_id INTEGER,
	event_name VARCHAR(120) NOT NULL,
	topic VARCHAR(66) NOT NULL,
	data JSON NOT NULL,
	log_index INTEGER NOT NULL,
	block_number INTEGER NOT NULL,
	emitted_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(contract_id) REFERENCES smart_contracts (id) ON DELETE CASCADE,
	FOREIGN KEY(call_id) REFERENCES contract_calls (id) ON DELETE SET NULL
);
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version VALUES('zz10_match_statistics');
CREATE INDEX ix_markets_id ON markets (id);
CREATE INDEX ix_markets_market_type ON markets (market_type);
CREATE INDEX ix_edges_id ON edges (id);
CREATE INDEX idx_edges_status ON edges (status);
CREATE INDEX idx_edges_roi ON edges (roi DESC);
CREATE INDEX idx_model_perf_certified ON model_performances (certified);
CREATE INDEX ix_model_performances_id ON model_performances (id);
CREATE INDEX ix_bankroll_states_id ON bankroll_states (id);
CREATE INDEX ix_decision_logs_match_id ON decision_logs (match_id);
CREATE INDEX ix_decision_logs_id ON decision_logs (id);
CREATE INDEX ix_decision_logs_prediction_id ON decision_logs (prediction_id);
CREATE INDEX idx_decision_logs_match ON decision_logs (match_id);
CREATE INDEX idx_teams_external_id ON teams (external_id);
CREATE INDEX ix_teams_external_id ON teams (external_id);
CREATE INDEX idx_teams_name ON teams (name);
CREATE INDEX ix_teams_name ON teams (name);
CREATE INDEX ix_teams_id ON teams (id);
CREATE INDEX ix_ai_performances_id ON ai_performances (id);
CREATE INDEX ix_subscription_plans_id ON subscription_plans (id);
CREATE UNIQUE INDEX ix_user_subscriptions_api_key_hash ON user_subscriptions (api_key_hash);
CREATE INDEX ix_user_subscriptions_id ON user_subscriptions (id);
CREATE INDEX idx_audit_timestamp ON audit_logs (timestamp);
CREATE INDEX idx_audit_actor ON audit_logs (actor);
CREATE INDEX idx_audit_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_id ON audit_logs (id);
CREATE INDEX ix_training_datasets_id ON training_datasets (id);
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE UNIQUE INDEX ix_users_telegram_id ON users (telegram_id);
CREATE INDEX ix_users_university ON users (university);
CREATE INDEX ix_users_faculty ON users (faculty);
CREATE INDEX ix_users_id ON users (id);
CREATE INDEX ix_users_department ON users (department);
CREATE UNIQUE INDEX ix_users_wallet_address ON users (wallet_address);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE UNIQUE INDEX ix_users_google_id ON users (google_id);
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role ON users (role);
CREATE UNIQUE INDEX ix_training_jobs_job_id ON training_jobs (job_id);
CREATE INDEX idx_training_jobs_status ON training_jobs (status);
CREATE INDEX ix_training_jobs_id ON training_jobs (id);
CREATE INDEX idx_token_blocklist_jti ON token_blocklist (jti);
CREATE UNIQUE INDEX ix_token_blocklist_jti ON token_blocklist (jti);
CREATE INDEX ix_token_blocklist_id ON token_blocklist (id);
CREATE INDEX idx_vitcoin_price_calculated_at ON vitcoin_price_history (calculated_at);
CREATE INDEX idx_webhook_events_provider ON webhook_events (provider);
CREATE INDEX idx_webhook_events_provider_received ON webhook_events (provider, received_at);
CREATE INDEX idx_webhook_events_reference ON webhook_events (reference);
CREATE INDEX idx_webhook_events_received_at ON webhook_events (received_at);
CREATE INDEX ix_task_categories_id ON task_categories (id);
CREATE UNIQUE INDEX ix_background_task_status_task_name ON background_task_status (task_name);
CREATE INDEX ix_background_task_status_id ON background_task_status (id);
CREATE UNIQUE INDEX ix_vit_blocks_height ON vit_blocks (height);
CREATE INDEX ix_vit_blocks_id ON vit_blocks (id);
CREATE UNIQUE INDEX ix_vit_blocks_hash ON vit_blocks (hash);
CREATE INDEX ix_vit_blocks_proposer ON vit_blocks (proposer);
CREATE UNIQUE INDEX ix_validator_stakes_address ON validator_stakes (address);
CREATE INDEX ix_validator_stakes_active ON validator_stakes (active);
CREATE INDEX ix_validator_stakes_id ON validator_stakes (id);
CREATE INDEX ix_core_accounts_owner_id ON core_accounts (owner_id);
CREATE UNIQUE INDEX ix_core_assets_symbol ON core_assets (symbol);
CREATE INDEX ix_core_wallet_audit_wallet_id ON core_wallet_audit (wallet_id);
CREATE INDEX ix_consensus_challenges_epoch ON consensus_challenges (epoch);
CREATE INDEX ix_consensus_challenges_node_id ON consensus_challenges (node_id);
CREATE INDEX ix_consensus_states_height ON consensus_states (height);
CREATE INDEX ix_consensus_states_node_id ON consensus_states (node_id);
CREATE INDEX ix_chain_blocks_prev_hash ON chain_blocks (prev_hash);
CREATE INDEX ix_chain_blocks_timestamp ON chain_blocks (timestamp);
CREATE INDEX ix_chain_blocks_validator_id ON chain_blocks (validator_id);
CREATE UNIQUE INDEX ix_chain_blocks_block_hash ON chain_blocks (block_hash);
CREATE INDEX ix_p2p_peers_last_seen ON p2p_peers (last_seen);
CREATE UNIQUE INDEX ix_authz_permissions_slug ON authz_permissions (slug);
CREATE UNIQUE INDEX ix_authz_roles_slug ON authz_roles (slug);
CREATE UNIQUE INDEX ix_authz_resources_slug ON authz_resources (slug);
CREATE INDEX ix_authz_policies_resource_pattern ON authz_policies (resource_pattern);
CREATE INDEX ix_authz_policies_action_pattern ON authz_policies (action_pattern);
CREATE UNIQUE INDEX ix_global_identities_email ON global_identities (email);
CREATE UNIQUE INDEX ix_global_identities_phone ON global_identities (phone);
CREATE UNIQUE INDEX ix_global_identities_username ON global_identities (username);
CREATE UNIQUE INDEX ix_global_identities_gid ON global_identities (gid);
CREATE INDEX idx_oracle_match_id ON oracle_results (match_id);
CREATE INDEX idx_oracle_dispute ON oracle_results (dispute_flag);
CREATE INDEX idx_bc_tx_type ON blockchain_transactions (tx_type);
CREATE INDEX idx_bc_tx_created ON blockchain_transactions (created_at);
CREATE INDEX idx_bc_tx_entity ON blockchain_transactions (entity_type, entity_id);
CREATE INDEX idx_bc_tx_match ON blockchain_transactions (match_id);
CREATE INDEX idx_signal_category ON marketplace_signals (category);
CREATE INDEX idx_signal_active ON marketplace_signals (is_active);
CREATE INDEX ix_model_metadata_id ON model_metadata (id);
CREATE UNIQUE INDEX ix_model_metadata_key ON model_metadata ("key");
CREATE INDEX ix_ai_prediction_audit_id ON ai_prediction_audit (id);
CREATE INDEX ix_ai_prediction_audit_match_id ON ai_prediction_audit (match_id);
CREATE UNIQUE INDEX ix_ai_insights_match_id ON ai_insights (match_id);
CREATE INDEX ix_ai_insights_id ON ai_insights (id);
CREATE INDEX ix_polling_data_election_id ON polling_data (election_id);
CREATE INDEX ix_elections_id ON elections (id);
CREATE INDEX ix_elections_status ON elections (status);
CREATE INDEX ix_elections_election_type ON elections (election_type);
CREATE INDEX ix_elections_country ON elections (country);
CREATE INDEX ix_policy_proposals_id ON policy_proposals (id);
CREATE INDEX ix_policy_proposals_category ON policy_proposals (category);
CREATE INDEX ix_policy_proposals_status ON policy_proposals (status);
CREATE INDEX ix_campus_circles_id ON campus_circles (id);
CREATE INDEX ix_campus_circles_university ON campus_circles (university);
CREATE INDEX ix_dev_api_plans_id ON dev_api_plans (id);
CREATE INDEX ix_social_signals_id ON social_signals (id);
CREATE UNIQUE INDEX ix_social_signals_deduplication_key ON social_signals (deduplication_key);
CREATE INDEX ix_social_signals_topic ON social_signals (topic);
CREATE INDEX ix_social_signals_source ON social_signals (source);
CREATE INDEX ix_bridge_pools_id ON bridge_pools (id);
CREATE INDEX idx_bridge_pool_assets ON bridge_pools (asset_from, asset_to);
CREATE INDEX ix_iq_test_questions_id ON iq_test_questions (id);
CREATE INDEX ix_oracle_mic_episodes_id ON oracle_mic_episodes (id);
CREATE INDEX ix_prophecy_chapters_id ON prophecy_chapters (id);
CREATE INDEX ix_node_activities_node_id ON node_activities (node_id);
CREATE INDEX ix_node_activities_recorded_at ON node_activities (recorded_at);
CREATE INDEX idx_node_activity_type ON node_activities (activity_type);
CREATE INDEX idx_node_activity_recorded_at ON node_activities (recorded_at);
CREATE INDEX idx_node_activity_node_id ON node_activities (node_id);
CREATE INDEX ix_network_snapshots_snapshot_at ON network_snapshots (snapshot_at);
CREATE INDEX idx_network_snapshot_at ON network_snapshots (snapshot_at);
CREATE INDEX ix_match_feature_store_league ON match_feature_store (league);
CREATE INDEX ix_match_feature_store_id ON match_feature_store (id);
CREATE INDEX ix_feature_store_league_kickoff ON match_feature_store (league, kickoff_time);
CREATE UNIQUE INDEX ix_match_feature_store_match_id ON match_feature_store (match_id);
CREATE INDEX ix_pipeline_runs_id ON pipeline_runs (id);
CREATE INDEX ix_matches_fingerprint ON matches (fingerprint);
CREATE INDEX ix_matches_market_type ON matches (market_type);
CREATE INDEX ix_matches_sport ON matches (sport);
CREATE INDEX idx_matches_status ON matches (status);
CREATE INDEX ix_matches_id ON matches (id);
CREATE INDEX idx_matches_kickoff ON matches (kickoff_time);
CREATE INDEX ix_matches_source ON matches (source);
CREATE UNIQUE INDEX ix_matches_external_id ON matches (external_id);
CREATE INDEX ix_training_guide_steps_id ON training_guide_steps (id);
CREATE INDEX idx_email_tokens_hash ON email_tokens (token_hash);
CREATE INDEX idx_email_tokens_user ON email_tokens (user_id);
CREATE UNIQUE INDEX ix_email_tokens_token_hash ON email_tokens (token_hash);
CREATE INDEX ix_email_tokens_id ON email_tokens (id);
CREATE INDEX idx_wallets_is_frozen ON wallets (is_frozen);
CREATE INDEX idx_wallets_user_id ON wallets (user_id);
CREATE UNIQUE INDEX ix_platform_secrets_key ON platform_secrets ("key");
CREATE INDEX ix_notifications_user_id ON notifications (user_id);
CREATE INDEX ix_notifications_id ON notifications (id);
CREATE INDEX ix_notification_preferences_id ON notification_preferences (id);
CREATE INDEX ix_push_subscriptions_user_id ON push_subscriptions (user_id);
CREATE UNIQUE INDEX ix_user_trust_scores_user_id ON user_trust_scores (user_id);
CREATE INDEX idx_trust_tier ON user_trust_scores (risk_tier);
CREATE INDEX ix_user_trust_scores_id ON user_trust_scores (id);
CREATE INDEX idx_trust_composite ON user_trust_scores (composite_score);
CREATE INDEX idx_flag_user_id ON fraud_flags (user_id);
CREATE INDEX idx_flag_status ON fraud_flags (status);
CREATE INDEX ix_fraud_flags_user_id ON fraud_flags (user_id);
CREATE INDEX idx_flag_severity ON fraud_flags (severity);
CREATE INDEX ix_fraud_flags_id ON fraud_flags (id);
CREATE INDEX idx_flag_category ON fraud_flags (category);
CREATE INDEX idx_flag_created ON fraud_flags (created_at);
CREATE INDEX ix_risk_events_user_id ON risk_events (user_id);
CREATE INDEX idx_risk_event_user ON risk_events (user_id);
CREATE INDEX ix_risk_events_id ON risk_events (id);
CREATE INDEX idx_risk_event_rule ON risk_events (rule_code);
CREATE INDEX idx_risk_event_created ON risk_events (created_at);
CREATE INDEX ix_risk_events_rule_code ON risk_events (rule_code);
CREATE UNIQUE INDEX ix_identity_organizations_slug ON identity_organizations (slug);
CREATE INDEX ix_identity_workspace_settings_user_id ON identity_workspace_settings (user_id);
CREATE INDEX ix_identity_workspace_settings_key ON identity_workspace_settings ("key");
CREATE INDEX idx_system_ids_user ON system_ids (user_id);
CREATE UNIQUE INDEX ix_system_ids_sid ON system_ids (sid);
CREATE INDEX idx_system_ids_sid ON system_ids (sid);
CREATE INDEX ix_tasks_id ON tasks (id);
CREATE INDEX ix_slash_events_reason ON slash_events (reason);
CREATE INDEX ix_slash_events_validator_address ON slash_events (validator_address);
CREATE INDEX ix_slash_events_id ON slash_events (id);
CREATE INDEX ix_slash_events_validator_reason ON slash_events (validator_address, reason);
CREATE INDEX ix_consensus_responses_node_id ON consensus_responses (node_id);
CREATE INDEX ix_chain_transactions_to_address ON chain_transactions (to_address);
CREATE INDEX ix_chain_transactions_status ON chain_transactions (status);
CREATE INDEX ix_chain_transactions_block_height ON chain_transactions (block_height);
CREATE INDEX ix_chain_transactions_from_address ON chain_transactions (from_address);
CREATE INDEX ix_chain_transactions_timestamp ON chain_transactions (timestamp);
CREATE INDEX idx_authz_user_roles_user ON authz_user_roles (user_id);
CREATE INDEX idx_authz_user_roles_role ON authz_user_roles (role_id);
CREATE INDEX idx_authz_role_perms_role ON authz_role_permissions (role_id);
CREATE INDEX idx_authz_role_perms_perm ON authz_role_permissions (permission_id);
CREATE UNIQUE INDEX ix_identity_sessions_refresh_token ON identity_sessions (refresh_token);
CREATE UNIQUE INDEX ix_identity_sessions_session_token ON identity_sessions (session_token);
CREATE UNIQUE INDEX idx_device_identity ON trusted_devices (identity_id, device_id);
CREATE INDEX idx_validator_status ON validator_profiles (status);
CREATE INDEX idx_validator_user_id ON validator_profiles (user_id);
CREATE INDEX idx_validator_trust_score ON validator_profiles (trust_score);
CREATE INDEX idx_consensus_status ON consensus_predictions (status);
CREATE INDEX idx_consensus_match_id ON consensus_predictions (match_id);
CREATE INDEX idx_bc_stake_status ON user_stakes (status);
CREATE INDEX idx_stake_user_id ON user_stakes (user_id);
CREATE INDEX idx_stake_match_id ON user_stakes (match_id);
CREATE INDEX idx_dispute_match_id ON oracle_disputes (match_id);
CREATE INDEX idx_dispute_status ON oracle_disputes (status);
CREATE INDEX idx_agent_app_user ON agent_applications (user_id);
CREATE INDEX idx_agent_app_status ON agent_applications (status);
CREATE INDEX ix_gov_proposals_id ON gov_proposals (id);
CREATE INDEX ix_gov_proposals_proposer_id ON gov_proposals (proposer_id);
CREATE INDEX idx_gov_proposal_proposer_id ON gov_proposals (proposer_id);
CREATE INDEX idx_gov_proposal_status ON gov_proposals (status);
CREATE INDEX ix_gov_configs_id ON gov_configs (id);
CREATE INDEX ix_candidates_election_id ON candidates (election_id);
CREATE INDEX ix_candidates_id ON candidates (id);
CREATE INDEX ix_election_polls_election_id ON election_polls (election_id);
CREATE INDEX ix_election_polls_id ON election_polls (id);
CREATE INDEX ix_academic_courses_course_code ON academic_courses (course_code);
CREATE INDEX ix_academic_courses_faculty ON academic_courses (faculty);
CREATE INDEX ix_academic_courses_id ON academic_courses (id);
CREATE INDEX ix_academic_courses_department ON academic_courses (department);
CREATE INDEX ix_academic_courses_level ON academic_courses (level);
CREATE INDEX ix_academic_courses_university ON academic_courses (university);
CREATE INDEX ix_campus_posts_id ON campus_posts (id);
CREATE INDEX idx_gig_status ON campus_gigs (status);
CREATE INDEX idx_gig_uni ON campus_gigs (university);
CREATE INDEX ix_campus_gigs_university ON campus_gigs (university);
CREATE INDEX ix_campus_gigs_id ON campus_gigs (id);
CREATE INDEX ix_marketplace_listings_approval_status ON marketplace_listings (approval_status);
CREATE INDEX idx_listing_category ON marketplace_listings (category);
CREATE INDEX ix_marketplace_listings_creator_id ON marketplace_listings (creator_id);
CREATE INDEX idx_listing_is_active ON marketplace_listings (is_active);
CREATE INDEX ix_marketplace_listings_id ON marketplace_listings (id);
CREATE INDEX idx_listing_approval_status ON marketplace_listings (approval_status);
CREATE UNIQUE INDEX ix_marketplace_listings_slug ON marketplace_listings (slug);
CREATE INDEX idx_listing_creator_id ON marketplace_listings (creator_id);
CREATE UNIQUE INDEX ix_referral_codes_code ON referral_codes (code);
CREATE INDEX ix_referral_codes_id ON referral_codes (id);
CREATE INDEX ix_referral_uses_id ON referral_uses (id);
CREATE INDEX ix_referral_uses_referrer_id ON referral_uses (referrer_id);
CREATE INDEX ix_dev_api_keys_user_id ON dev_api_keys (user_id);
CREATE INDEX idx_dev_key_user_id ON dev_api_keys (user_id);
CREATE INDEX idx_dev_key_is_active ON dev_api_keys (is_active);
CREATE INDEX idx_dev_key_prefix ON dev_api_keys (key_prefix);
CREATE INDEX ix_dev_api_keys_id ON dev_api_keys (id);
CREATE INDEX ix_offer_completions_status ON offer_completions (status);
CREATE INDEX ix_offer_completions_id ON offer_completions (id);
CREATE INDEX ix_offer_completions_user_id ON offer_completions (user_id);
CREATE INDEX ix_offer_completions_provider ON offer_completions (provider);
CREATE INDEX idx_offer_completions_status ON offer_completions (status);
CREATE INDEX ix_offer_completions_provider_event_id ON offer_completions (provider_event_id);
CREATE INDEX idx_vit_identity_agent ON vit_identities (agent_name);
CREATE UNIQUE INDEX ix_vit_identities_did ON vit_identities (did);
CREATE INDEX idx_vit_identity_user_id ON vit_identities (user_id);
CREATE INDEX idx_vit_identity_subject_type ON vit_identities (subject_type);
CREATE INDEX ix_social_opportunities_id ON social_opportunities (id);
CREATE INDEX ix_social_opportunities_signal_id ON social_opportunities (signal_id);
CREATE INDEX ix_bridge_transactions_user_id ON bridge_transactions (user_id);
CREATE INDEX ix_bridge_transactions_pool_id ON bridge_transactions (pool_id);
CREATE INDEX idx_bridge_tx_user_id ON bridge_transactions (user_id);
CREATE INDEX ix_bridge_transactions_id ON bridge_transactions (id);
CREATE INDEX idx_bridge_tx_status ON bridge_transactions (status);
CREATE INDEX idx_bridge_tx_created_at ON bridge_transactions (created_at);
CREATE UNIQUE INDEX ix_bridge_transactions_tx_hash ON bridge_transactions (tx_hash);
CREATE INDEX ix_user_iq_test_results_user_id ON user_iq_test_results (user_id);
CREATE INDEX ix_user_iq_test_results_id ON user_iq_test_results (id);
CREATE INDEX idx_kyc_status ON kyc_submissions (status);
CREATE INDEX idx_kyc_user_id ON kyc_submissions (user_id);
CREATE INDEX ix_user_prophecy_progress_user_id ON user_prophecy_progress (user_id);
CREATE INDEX ix_user_prophecy_progress_id ON user_prophecy_progress (id);
CREATE INDEX idx_module_tj_submitted_at ON module_training_jobs (submitted_at);
CREATE INDEX idx_module_tj_status ON module_training_jobs (status);
CREATE INDEX idx_module_tj_user_id ON module_training_jobs (user_id);
CREATE INDEX ix_predictions_status ON predictions (status);
CREATE INDEX idx_predictions_timestamp ON predictions (timestamp DESC);
CREATE UNIQUE INDEX ix_predictions_request_hash ON predictions (request_hash);
CREATE INDEX ix_predictions_id ON predictions (id);
CREATE INDEX idx_predictions_match_id ON predictions (match_id);
CREATE INDEX ix_predictions_user_id ON predictions (user_id);
CREATE INDEX idx_ai_match_source ON ai_predictions (match_id, source);
CREATE INDEX idx_ai_predictions_match ON ai_predictions (match_id);
CREATE INDEX idx_ai_timestamp ON ai_predictions (timestamp);
CREATE INDEX ix_ai_predictions_id ON ai_predictions (id);
CREATE INDEX idx_ai_predictions_source ON ai_predictions (source);
CREATE INDEX ix_ai_signal_cache_id ON ai_signal_cache (id);
CREATE INDEX idx_ai_signal_cache_match ON ai_signal_cache (match_id);
CREATE INDEX ix_iot_events_id ON iot_events (id);
CREATE INDEX idx_iot_events_type ON iot_events (event_type);
CREATE INDEX idx_iot_events_match ON iot_events (match_id);
CREATE INDEX idx_iot_events_created ON iot_events (created_at);
CREATE INDEX idx_iot_events_source ON iot_events (source);
CREATE INDEX idx_agent_insights_agent ON agent_insights (agent_name);
CREATE INDEX idx_agent_insights_match ON agent_insights (match_id);
CREATE INDEX idx_agent_insights_type ON agent_insights (insight_type);
CREATE INDEX idx_agent_insights_created ON agent_insights (created_at);
CREATE INDEX ix_agent_insights_id ON agent_insights (id);
CREATE INDEX idx_wallet_profiles_wallet_id ON wallet_profiles (wallet_id);
CREATE INDEX idx_wallet_tx_wallet_id ON wallet_transactions (wallet_id);
CREATE INDEX idx_wallet_tx_type ON wallet_transactions (type);
CREATE INDEX idx_wallet_tx_currency ON wallet_transactions (currency);
CREATE INDEX idx_wallet_tx_status ON wallet_transactions (status);
CREATE INDEX idx_wallet_tx_created_at ON wallet_transactions (created_at);
CREATE INDEX idx_wallet_tx_user_id ON wallet_transactions (user_id);
CREATE INDEX idx_withdrawal_status ON withdrawal_requests (status);
CREATE INDEX idx_withdrawal_user_id ON withdrawal_requests (user_id);
CREATE INDEX idx_withdrawal_requested_at ON withdrawal_requests (requested_at);
CREATE INDEX idx_vault_wallet_id ON savings_vaults (wallet_id);
CREATE INDEX idx_vault_type ON savings_vaults (vault_type);
CREATE INDEX idx_vault_user_id ON savings_vaults (user_id);
CREATE INDEX idx_p2p_offer_status ON p2p_offers (status);
CREATE INDEX idx_p2p_offer_user_id ON p2p_offers (user_id);
CREATE INDEX idx_p2p_offer_currency ON p2p_offers (currency);
CREATE INDEX idx_p2p_offer_type ON p2p_offers (offer_type);
CREATE INDEX ix_identity_teams_organization_id ON identity_teams (organization_id);
CREATE UNIQUE INDEX ix_identity_teams_slug ON identity_teams (slug);
CREATE INDEX idx_org_member_org_id ON identity_organization_members (organization_id);
CREATE INDEX idx_org_member_user_id ON identity_organization_members (user_id);
CREATE INDEX ix_identity_organization_members_organization_id ON identity_organization_members (organization_id);
CREATE INDEX ix_identity_organization_members_user_id ON identity_organization_members (user_id);
CREATE INDEX ix_user_task_completions_id ON user_task_completions (id);
CREATE INDEX ix_slash_appeals_id ON slash_appeals (id);
CREATE INDEX ix_slash_appeals_status ON slash_appeals (status);
CREATE INDEX ix_slash_appeals_validator_address ON slash_appeals (validator_address);
CREATE INDEX ix_slash_appeals_slash_event_id ON slash_appeals (slash_event_id);
CREATE INDEX idx_balance_lookup ON core_balances (wallet_id, asset_symbol);
CREATE INDEX ix_core_addresses_address ON core_addresses (address);
CREATE INDEX ix_core_addresses_network ON core_addresses (network);
CREATE INDEX idx_val_pred_match_id ON validator_predictions (match_id);
CREATE INDEX idx_val_pred_validator_id ON validator_predictions (validator_id);
CREATE INDEX idx_settlement_match_id ON match_settlements (match_id);
CREATE INDEX idx_slash_validator_id ON validator_slash_events (validator_id);
CREATE INDEX idx_slash_user_id ON validator_slash_events (user_id);
CREATE INDEX idx_slash_slashed_at ON validator_slash_events (slashed_at);
CREATE INDEX ix_gov_votes_voter_id ON gov_votes (voter_id);
CREATE INDEX ix_gov_votes_proposal_id ON gov_votes (proposal_id);
CREATE INDEX ix_gov_votes_id ON gov_votes (id);
CREATE INDEX idx_gov_vote_proposal_id ON gov_votes (proposal_id);
CREATE INDEX idx_gov_vote_voter_id ON gov_votes (voter_id);
CREATE INDEX ix_evidence_snapshots_match_id ON evidence_snapshots (match_id);
CREATE INDEX ix_market_mappings_match_id ON market_mappings (match_id);
CREATE INDEX ix_market_mappings_internal_market_id ON market_mappings (internal_market_id);
CREATE INDEX ix_market_mappings_external_match_id ON market_mappings (external_match_id);
CREATE INDEX ix_market_mappings_id ON market_mappings (id);
CREATE INDEX ix_affiliate_clicks_id ON affiliate_clicks (id);
CREATE INDEX ix_watchlist_items_match_id ON watchlist_items (match_id);
CREATE INDEX ix_watchlist_items_user_id ON watchlist_items (user_id);
CREATE INDEX ix_election_predictions_id ON election_predictions (id);
CREATE INDEX ix_election_predictions_user_id ON election_predictions (user_id);
CREATE INDEX ix_election_predictions_election_id ON election_predictions (election_id);
CREATE INDEX idx_resource_type ON academic_resources (resource_type);
CREATE INDEX ix_academic_resources_id ON academic_resources (id);
CREATE INDEX idx_resource_course ON academic_resources (course_id);
CREATE INDEX ix_campus_comments_id ON campus_comments (id);
CREATE INDEX ix_marketplace_usage_logs_id ON marketplace_usage_logs (id);
CREATE INDEX idx_usage_called_at ON marketplace_usage_logs (called_at);
CREATE INDEX idx_usage_listing_id ON marketplace_usage_logs (listing_id);
CREATE INDEX ix_marketplace_usage_logs_caller_id ON marketplace_usage_logs (caller_id);
CREATE INDEX ix_marketplace_usage_logs_listing_id ON marketplace_usage_logs (listing_id);
CREATE INDEX idx_usage_caller_id ON marketplace_usage_logs (caller_id);
CREATE INDEX ix_marketplace_ratings_listing_id ON marketplace_ratings (listing_id);
CREATE INDEX ix_marketplace_ratings_id ON marketplace_ratings (id);
CREATE INDEX idx_rating_listing_id ON marketplace_ratings (listing_id);
CREATE INDEX ix_marketplace_ratings_user_id ON marketplace_ratings (user_id);
CREATE INDEX ix_marketplace_stakes_staker_id ON marketplace_stakes (staker_id);
CREATE INDEX idx_stake_listing_id ON marketplace_stakes (listing_id);
CREATE INDEX ix_marketplace_stakes_listing_id ON marketplace_stakes (listing_id);
CREATE INDEX ix_marketplace_stakes_id ON marketplace_stakes (id);
CREATE INDEX idx_stake_staker_id ON marketplace_stakes (staker_id);
CREATE INDEX idx_mkt_stake_status ON marketplace_stakes (status);
CREATE INDEX ix_marketplace_stakes_status ON marketplace_stakes (status);
CREATE INDEX ix_marketplace_slash_events_id ON marketplace_slash_events (id);
CREATE INDEX idx_slash_created_at ON marketplace_slash_events (created_at);
CREATE INDEX idx_slash_listing_id ON marketplace_slash_events (listing_id);
CREATE INDEX ix_marketplace_slash_events_listing_id ON marketplace_slash_events (listing_id);
CREATE INDEX ix_dev_api_usage_logs_user_id ON dev_api_usage_logs (user_id);
CREATE INDEX ix_dev_api_usage_logs_api_key_id ON dev_api_usage_logs (api_key_id);
CREATE INDEX idx_dev_usage_key_id ON dev_api_usage_logs (api_key_id);
CREATE INDEX ix_dev_api_usage_logs_id ON dev_api_usage_logs (id);
CREATE INDEX idx_dev_usage_user_id ON dev_api_usage_logs (user_id);
CREATE INDEX idx_dev_usage_called_at ON dev_api_usage_logs (called_at);
CREATE INDEX ix_postback_audit_logs_provider ON postback_audit_logs (provider);
CREATE INDEX ix_postback_audit_logs_id ON postback_audit_logs (id);
CREATE INDEX ix_postback_audit_logs_offer_completion_id ON postback_audit_logs (offer_completion_id);
CREATE INDEX idx_vc_identity_id ON verifiable_credentials (identity_id);
CREATE INDEX idx_vc_type ON verifiable_credentials (credential_type);
CREATE INDEX idx_vc_revoked ON verifiable_credentials (revoked);
CREATE INDEX ix_verifiable_credentials_credential_type ON verifiable_credentials (credential_type);
CREATE INDEX ix_social_candidates_opportunity_id ON social_candidates (opportunity_id);
CREATE INDEX ix_social_candidates_state ON social_candidates (state);
CREATE INDEX ix_social_candidates_id ON social_candidates (id);
CREATE INDEX ix_bridge_audit_logs_transaction_id ON bridge_audit_logs (transaction_id);
CREATE INDEX ix_bridge_audit_logs_id ON bridge_audit_logs (id);
CREATE INDEX idx_kyc_audit_submission ON kyc_audit_events (submission_id);
CREATE INDEX idx_module_tgs_job_id ON module_training_guide_steps (job_id);
CREATE INDEX idx_clv_match ON clv_entries (match_id);
CREATE INDEX ix_clv_entries_id ON clv_entries (id);
CREATE INDEX idx_clv_bet_side ON clv_entries (bet_side);
CREATE INDEX idx_wallet_subs_user_id ON wallet_user_subscriptions (user_id);
CREATE INDEX idx_wallet_subs_expires_at ON wallet_user_subscriptions (expires_at);
CREATE INDEX idx_wallet_subs_status ON wallet_user_subscriptions (status);
CREATE INDEX idx_p2p_order_status ON p2p_orders (status);
CREATE INDEX idx_p2p_order_seller_id ON p2p_orders (seller_id);
CREATE INDEX idx_p2p_order_buyer_id ON p2p_orders (buyer_id);
CREATE INDEX idx_p2p_order_offer_id ON p2p_orders (offer_id);
CREATE INDEX ix_identity_team_members_team_id ON identity_team_members (team_id);
CREATE INDEX ix_identity_team_members_user_id ON identity_team_members (user_id);
CREATE INDEX idx_team_member_team_id ON identity_team_members (team_id);
CREATE INDEX idx_team_member_user_id ON identity_team_members (user_id);
CREATE INDEX ix_rollover_certificates_fixture_id ON rollover_certificates (fixture_id);
CREATE INDEX ix_rollover_certificates_id ON rollover_certificates (id);
CREATE INDEX idx_rollover_status ON rollover_certificates (status);
CREATE INDEX ix_rollover_certificates_pipeline_run_id ON rollover_certificates (pipeline_run_id);
CREATE INDEX idx_rollover_pipeline_run ON rollover_certificates (pipeline_run_id);
CREATE INDEX ix_rollover_certificates_status ON rollover_certificates (status);
CREATE INDEX idx_rollover_fixture ON rollover_certificates (fixture_id);
CREATE INDEX idx_appeal_status ON validator_appeals (status);
CREATE INDEX idx_appeal_validator ON validator_appeals (validator_id);
CREATE INDEX idx_appeal_user ON validator_appeals (user_id);
CREATE INDEX ix_market_requirement_results_evidence_snapshot_id ON market_requirement_results (evidence_snapshot_id);
CREATE INDEX ix_market_requirement_results_market_key ON market_requirement_results (market_key);
CREATE INDEX ix_social_publication_records_candidate_id ON social_publication_records (candidate_id);
CREATE INDEX ix_social_publication_records_id ON social_publication_records (id);
CREATE INDEX ix_social_publication_records_status ON social_publication_records (status);
CREATE INDEX ix_social_publication_records_platform ON social_publication_records (platform);
COMMIT;
