from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "marketplace_posts" ADD COLUMN "site_id" UUID;
        CREATE INDEX IF NOT EXISTS "idx_marketplace_site_id_post" ON "marketplace_posts" ("site_id");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_marketplace_site_id_post";
        ALTER TABLE "marketplace_posts" DROP COLUMN "site_id";
    """
