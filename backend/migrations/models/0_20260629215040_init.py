from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "leaderboard_weights" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "is_deleted" BOOL NOT NULL  DEFAULT False,
    "deleted_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "weight_id" UUID NOT NULL UNIQUE,
    "leaderboard" VARCHAR(16) NOT NULL,
    "w_uptime" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "w_speed" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "w_authenticity" DOUBLE PRECISION NOT NULL  DEFAULT 0,
    "w_review" DOUBLE PRECISION NOT NULL  DEFAULT 0
);
CREATE INDEX IF NOT EXISTS "idx_leaderboard_is_dele_4f5668" ON "leaderboard_weights" ("is_deleted");
CREATE INDEX IF NOT EXISTS "idx_leaderboard_weight__a4b74e" ON "leaderboard_weights" ("weight_id");
CREATE INDEX IF NOT EXISTS "idx_leaderboard_leaderb_6d2959" ON "leaderboard_weights" ("leaderboard");
COMMENT ON TABLE "leaderboard_weights" IS '每个分榜一套权重。';
CREATE TABLE IF NOT EXISTS "marketplace_posts" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "is_deleted" BOOL NOT NULL  DEFAULT False,
    "deleted_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "post_id" UUID NOT NULL UNIQUE,
    "author_id" UUID NOT NULL,
    "post_type" VARCHAR(16) NOT NULL,
    "direction" VARCHAR(16) NOT NULL,
    "model_family" VARCHAR(32) NOT NULL,
    "rate" DECIMAL(8,4),
    "rpm" INT,
    "volume" VARCHAR(128),
    "settlement" VARCHAR(16),
    "note" TEXT,
    "status" VARCHAR(16) NOT NULL  DEFAULT 'open'
);
CREATE INDEX IF NOT EXISTS "idx_marketplace_is_dele_08413a" ON "marketplace_posts" ("is_deleted");
CREATE INDEX IF NOT EXISTS "idx_marketplace_post_id_63b23b" ON "marketplace_posts" ("post_id");
CREATE INDEX IF NOT EXISTS "idx_marketplace_author__84fc19" ON "marketplace_posts" ("author_id");
CREATE INDEX IF NOT EXISTS "idx_marketplace_model_f_8920ce" ON "marketplace_posts" ("model_family");
CREATE INDEX IF NOT EXISTS "idx_marketplace_status_b7586c" ON "marketplace_posts" ("status");
COMMENT ON TABLE "marketplace_posts" IS '站长广场（中转集市）帖子：批发倒卖 API 产能。';
CREATE TABLE IF NOT EXISTS "post_responses" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "is_deleted" BOOL NOT NULL  DEFAULT False,
    "deleted_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "response_id" UUID NOT NULL UNIQUE,
    "post_id" UUID NOT NULL,
    "responder_id" UUID NOT NULL,
    "status" VARCHAR(16) NOT NULL  DEFAULT 'pending'
);
CREATE INDEX IF NOT EXISTS "idx_post_respon_is_dele_e2e42b" ON "post_responses" ("is_deleted");
CREATE INDEX IF NOT EXISTS "idx_post_respon_respons_73a776" ON "post_responses" ("response_id");
CREATE INDEX IF NOT EXISTS "idx_post_respon_post_id_9788d1" ON "post_responses" ("post_id");
CREATE INDEX IF NOT EXISTS "idx_post_respon_respond_04cf56" ON "post_responses" ("responder_id");
COMMENT ON TABLE "post_responses" IS '广场对接记录。';
CREATE TABLE IF NOT EXISTS "probe_results" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "is_deleted" BOOL NOT NULL  DEFAULT False,
    "deleted_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "probe_id" UUID NOT NULL UNIQUE,
    "site_id" UUID NOT NULL,
    "probe_type" VARCHAR(16) NOT NULL,
    "probed_at" TIMESTAMPTZ NOT NULL,
    "target_model" VARCHAR(128),
    "ttfb_ms" INT,
    "total_ms" INT,
    "http_status" INT,
    "is_alive" BOOL NOT NULL  DEFAULT False,
    "is_authentic" BOOL,
    "error_sample" TEXT
);
CREATE INDEX IF NOT EXISTS "idx_probe_resul_is_dele_e4d4b8" ON "probe_results" ("is_deleted");
CREATE INDEX IF NOT EXISTS "idx_probe_resul_probe_i_9dbe8b" ON "probe_results" ("probe_id");
CREATE INDEX IF NOT EXISTS "idx_probe_resul_site_id_726d88" ON "probe_results" ("site_id");
CREATE INDEX IF NOT EXISTS "idx_probe_resul_probe_t_3b732d" ON "probe_results" ("probe_type");
CREATE INDEX IF NOT EXISTS "idx_probe_resul_probed__b9827a" ON "probe_results" ("probed_at");
COMMENT ON TABLE "probe_results" IS '单次探测结果。';
CREATE TABLE IF NOT EXISTS "relay_sites" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "is_deleted" BOOL NOT NULL  DEFAULT False,
    "deleted_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "site_id" UUID NOT NULL UNIQUE,
    "owner_id" UUID NOT NULL,
    "name" VARCHAR(128) NOT NULL,
    "slug" VARCHAR(128) NOT NULL,
    "site_url" VARCHAR(512),
    "base_url" VARCHAR(512) NOT NULL,
    "encrypted_key" TEXT NOT NULL,
    "key_hint" VARCHAR(32) NOT NULL,
    "probe_budget_daily" INT NOT NULL  DEFAULT 0,
    "declared_models" JSONB,
    "min_topup" DECIMAL(12,2),
    "pay_methods" VARCHAR(256),
    "rpm_limit" INT,
    "status" VARCHAR(24) NOT NULL  DEFAULT 'pending',
    "review_note" TEXT,
    "status_changed_at" TIMESTAMPTZ,
    "maintenance_windows" JSONB,
    "first_seen_at" TIMESTAMPTZ,
    "last_probe_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_relay_sites_is_dele_d923bc" ON "relay_sites" ("is_deleted");
CREATE INDEX IF NOT EXISTS "idx_relay_sites_site_id_bf8aff" ON "relay_sites" ("site_id");
CREATE INDEX IF NOT EXISTS "idx_relay_sites_owner_i_5d5ceb" ON "relay_sites" ("owner_id");
CREATE INDEX IF NOT EXISTS "idx_relay_sites_status_338cd1" ON "relay_sites" ("status");
COMMENT ON TABLE "relay_sites" IS '站长上架的中转站。';
CREATE TABLE IF NOT EXISTS "reviews" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "is_deleted" BOOL NOT NULL  DEFAULT False,
    "deleted_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "review_id" UUID NOT NULL UNIQUE,
    "site_id" UUID NOT NULL,
    "author_id" UUID NOT NULL,
    "review_type" VARCHAR(16) NOT NULL,
    "rating" INT NOT NULL,
    "content" TEXT,
    "verified" BOOL NOT NULL  DEFAULT False
);
CREATE INDEX IF NOT EXISTS "idx_reviews_is_dele_e9bc20" ON "reviews" ("is_deleted");
CREATE INDEX IF NOT EXISTS "idx_reviews_review__f63cf8" ON "reviews" ("review_id");
CREATE INDEX IF NOT EXISTS "idx_reviews_site_id_2d28d1" ON "reviews" ("site_id");
CREATE INDEX IF NOT EXISTS "idx_reviews_author__7dda7e" ON "reviews" ("author_id");
COMMENT ON TABLE "reviews" IS '评价（两类共表）。';
CREATE TABLE IF NOT EXISTS "site_scores" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "is_deleted" BOOL NOT NULL  DEFAULT False,
    "deleted_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "score_id" UUID NOT NULL UNIQUE,
    "site_id" UUID NOT NULL,
    "leaderboard" VARCHAR(16) NOT NULL,
    "uptime_score" DOUBLE PRECISION,
    "speed_score" DOUBLE PRECISION,
    "authenticity_score" DOUBLE PRECISION,
    "review_score" DOUBLE PRECISION,
    "composite_score" DOUBLE PRECISION,
    "rank" INT
);
CREATE INDEX IF NOT EXISTS "idx_site_scores_is_dele_242d6d" ON "site_scores" ("is_deleted");
CREATE INDEX IF NOT EXISTS "idx_site_scores_score_i_88ac06" ON "site_scores" ("score_id");
CREATE INDEX IF NOT EXISTS "idx_site_scores_site_id_cb4589" ON "site_scores" ("site_id");
CREATE INDEX IF NOT EXISTS "idx_site_scores_leaderb_56e1d7" ON "site_scores" ("leaderboard");
COMMENT ON TABLE "site_scores" IS '每个站 × 每个分榜一行，Worker 每轮探测后重算。';
CREATE TABLE IF NOT EXISTS "users" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "is_deleted" BOOL NOT NULL  DEFAULT False,
    "deleted_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" UUID NOT NULL UNIQUE,
    "email" VARCHAR(255) NOT NULL,
    "password_hash" VARCHAR(255) NOT NULL,
    "role" VARCHAR(16) NOT NULL  DEFAULT 'user',
    "wechat" VARCHAR(128),
    "qq" VARCHAR(32)
);
CREATE INDEX IF NOT EXISTS "idx_users_is_dele_9cdc79" ON "users" ("is_deleted");
CREATE INDEX IF NOT EXISTS "idx_users_user_id_a795d9" ON "users" ("user_id");
COMMENT ON TABLE "users" IS '用户与站长共用一张表，role=user|owner。';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
