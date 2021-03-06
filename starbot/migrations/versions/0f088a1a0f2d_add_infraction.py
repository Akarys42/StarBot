"""empty message

Revision ID: 0f088a1a0f2d
Revises: b7e301f75156
Create Date: 2022-02-28 11:58:55.680503

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0f088a1a0f2d"
down_revision = "b7e301f75156"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "infraction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("moderator_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("duration", sa.Interval(), nullable=True),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column(
            "type",
            sa.Enum("NOTE", "WARNING", "MUTE", "KICK", "BAN", name="infractiontypes"),
            nullable=True,
        ),
        sa.Column("cancelled", sa.Boolean(), nullable=False),
        sa.Column("dm_sent", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["guild_id"],
            ["guild.guild_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("infraction")
    # ### end Alembic commands ###
