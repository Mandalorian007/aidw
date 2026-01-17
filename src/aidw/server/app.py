"""FastAPI application and routes."""

import json
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Header, Request, Response

from aidw import __version__
from aidw.database import Database
from aidw.env import ensure_config_dir
from aidw.server.security import verify_webhook_signature
from aidw.server.webhook import (
    ParsedCommand,
    parse_command,
    parse_webhook_event,
    validate_command_context,
)

logger = logging.getLogger(__name__)

# Database instance
db: Database | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global db

    # Startup
    ensure_config_dir()
    db = Database()
    await db.connect()
    logger.info("AIDW server started")

    yield

    # Shutdown
    if db:
        await db.close()
    logger.info("AIDW server stopped")


app = FastAPI(
    title="AIDW",
    description="AI Dev Workflow - GitHub webhook server",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/goodbye")
async def goodbye():
    """Goodbye endpoint."""
    return {"message": "Goodbye, World!"}


async def process_command(cmd: ParsedCommand) -> None:
    """Process a parsed command in the background."""
    from aidw.commands import (
        build_command,
        iterate_command,
        oneshot_command,
        plan_command,
        refine_command,
    )

    logger.info(f"Processing command: {cmd.command} for {cmd.repo}#{cmd.issue_number}")

    try:
        if cmd.command == "plan":
            await plan_command.execute(cmd)
        elif cmd.command == "refine":
            await refine_command.execute(cmd)
        elif cmd.command == "build":
            await build_command.execute(cmd)
        elif cmd.command == "oneshot":
            await oneshot_command.execute(cmd)
        elif cmd.command == "iterate":
            await iterate_command.execute(cmd)
        else:
            logger.error(f"Unknown command: {cmd.command}")
    except Exception as e:
        logger.exception(f"Error processing command {cmd.command}: {e}")
        # TODO: Post error comment to GitHub


@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: Annotated[str | None, Header()] = None,
    body: bytes = Depends(verify_webhook_signature),
):
    """Handle GitHub webhook events."""
    if not x_github_event:
        return Response(status_code=400, content="Missing event header")

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return Response(status_code=400, content="Invalid JSON")

    # Parse webhook event
    context = parse_webhook_event(x_github_event, payload)
    if not context:
        # Not a relevant event
        return {"status": "ignored", "reason": "not a comment event"}

    # Parse command from comment
    cmd = parse_command(context)
    if not cmd:
        # No command found or user not allowed
        return {"status": "ignored", "reason": "no valid command"}

    # Validate command can run in this context
    error = validate_command_context(cmd)
    if error:
        logger.warning(f"Invalid command context: {error}")
        # TODO: Post error comment to GitHub
        return {"status": "error", "message": error}

    # Process command in background
    logger.info(f"Received command: @aidw {cmd.command} from {cmd.author}")
    background_tasks.add_task(process_command, cmd)

    return {
        "status": "accepted",
        "command": cmd.command,
        "repo": cmd.repo,
        "issue": cmd.issue_number,
        "pr": cmd.pr_number,
    }
