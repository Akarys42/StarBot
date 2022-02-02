# StarBot

**StarBot** is a highly configurable, general-purpose bot aiming to provide the essential functionalities needed to run your community while being an open-source alternative to larger bots.

Right now, while the bot is still in active development, no public instance is provided. If you would like to use our private instance, Luna 💫#6811, feel free to join [our server](https://discord.akarys.me) and shoot a message.

Our long term goal is for you to have everything you need to run your community by inviting the bot and typing a handful of commands. That said, we want to still make our bot configurable so it can truly fit your community.

# Self-hosting the Bot

As we do not provide managed instances *for the time being*, the only available option is for you to self-host. The only hard dependency of the bot is the [PostgreSQL](https://www.postgresql.org/) database.

For easier setup, you may wish to use our docker-compose setup. That will require you to create a `.env` file containing a `TOKEN` key mapping to your bot token.

We also have a container available at `ghcr.io/akarys42/starbot`. The image will also require a `DATABASE_URL` environment variable of the format `postgresql+asyncpg://$user:$password@$host:$port/$database`.

By default, the migrations aren't run. If you want the bot to automatically upgrade on startup, please set the environment variable `RUN_MIGRATION` to `1`. Alternatively, you can run `python -m alembic upgrade head` inside the container to migrate.

# Development Environment

Our docker-compose setup can be used for development. We recommend setting `DEBUG` to `1` and `TEST_GUILDS` to a comma-separated list of guilds you want the bot to instantaneously update in.

If you are interested in helping, please join [our server](https://discord.akarys.me) and introduce yourself in `#starbot`.

Our code is formatted using [Black](https://github.com/psf/black) and [ISort](https://github.com/PyCQA/isort). Please make sure to run `poetry run task precommit` before committing to make sure your code will always pass linting.

Thank you for your interest in our project!
