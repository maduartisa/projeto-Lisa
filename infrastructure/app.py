import os

from aws_cdk import App, Environment, Tags

from stacks.platform_stack import PlatformStack
from stacks.stage_config import StageConfig


app = App()
stage_name = app.node.try_get_context("environment") or "dev"
region = (
    app.node.try_get_context("region")
    or os.environ.get("CDK_DEFAULT_REGION")
    or "sa-east-1"
)
account = (
    app.node.try_get_context("account")
    or os.environ.get("CDK_DEFAULT_ACCOUNT")
)
config = StageConfig.for_name(stage_name)

stack = PlatformStack(
    app,
    f"CommercialPlatform-{config.name}",
    config=config,
    env=Environment(account=account, region=region),
    description=f"Shared multi-tenant platform foundation ({config.name})",
)
Tags.of(stack).add("Application", "commercial-platform")
Tags.of(stack).add("Environment", config.name)
Tags.of(stack).add("ManagedBy", "AWS-CDK")

app.synth()
