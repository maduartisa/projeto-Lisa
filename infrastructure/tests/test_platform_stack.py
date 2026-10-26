import unittest

from aws_cdk import App, Environment
from aws_cdk.assertions import Match, Template

from stacks.platform_stack import PlatformStack
from stacks.stage_config import StageConfig


class PlatformStackTest(unittest.TestCase):
    def setUp(self) -> None:
        app = App()
        stack = PlatformStack(
            app,
            "PlatformDevTest",
            config=StageConfig.for_name("dev"),
            env=Environment(region="sa-east-1"),
        )
        self.template = Template.from_stack(stack)

    def test_database_is_private_encrypted_and_protected(self) -> None:
        self.template.has_resource_properties(
            "AWS::RDS::DBInstance",
            {
                "DBName": "platform",
                "Engine": "postgres",
                "EngineVersion": "17.6",
                "PubliclyAccessible": False,
                "StorageEncrypted": True,
                "DeletionProtection": True,
                "MultiAZ": False,
                "BackupRetentionPeriod": 7,
            },
        )

    def test_database_ingress_is_limited_to_application_security_group(self) -> None:
        ingress_rules = self.template.find_resources("AWS::EC2::SecurityGroupIngress")
        postgres_rules = [
            resource["Properties"]
            for resource in ingress_rules.values()
            if resource["Properties"].get("FromPort") == 5432
        ]

        self.assertEqual(len(postgres_rules), 1)
        self.assertIn("SourceSecurityGroupId", postgres_rules[0])
        self.assertNotIn("CidrIp", postgres_rules[0])
        self.assertNotIn("CidrIpv6", postgres_rules[0])

    def test_application_egress_is_limited_to_https_and_postgres(self) -> None:
        security_groups = self.template.find_resources("AWS::EC2::SecurityGroup")
        application_groups = [
            resource["Properties"]
            for resource in security_groups.values()
            if resource["Properties"].get("GroupDescription")
            == "Security group reserved for private application tasks"
        ]
        self.assertEqual(len(application_groups), 1)
        inline_egress_ports = {
            rule.get("ToPort")
            for rule in application_groups[0].get("SecurityGroupEgress", [])
        }

        egress_rules = self.template.find_resources("AWS::EC2::SecurityGroupEgress")
        referenced_egress_ports = {
            resource["Properties"].get("ToPort")
            for resource in egress_rules.values()
            if resource["Properties"].get("GroupId")
        }

        self.assertEqual(inline_egress_ports, {443})
        self.assertEqual(referenced_egress_ports, {5432})

    def test_bucket_blocks_public_access_and_enforces_encryption(self) -> None:
        self.template.has_resource_properties(
            "AWS::S3::Bucket",
            {
                "VersioningConfiguration": {"Status": "Enabled"},
                "BucketEncryption": Match.any_value(),
                "PublicAccessBlockConfiguration": {
                    "BlockPublicAcls": True,
                    "BlockPublicPolicy": True,
                    "IgnorePublicAcls": True,
                    "RestrictPublicBuckets": True,
                },
            },
        )
        self.template.has_resource_properties(
            "AWS::S3::BucketPolicy",
            {
                "PolicyDocument": Match.object_like(
                    {
                        "Statement": Match.array_with(
                            [
                                Match.object_like(
                                    {
                                        "Action": "s3:*",
                                        "Effect": "Deny",
                                    }
                                )
                            ]
                        )
                    }
                )
            },
        )
    def test_base_includes_repositories_and_cluster_without_placeholder_services(self) -> None:
        self.template.resource_count_is("AWS::ECR::Repository", 3)
        self.template.resource_count_is("AWS::ECS::Cluster", 1)
        self.template.resource_count_is("AWS::ECS::Service", 0)
        self.template.resource_count_is("AWS::ElasticLoadBalancingV2::LoadBalancer", 0)

    def test_production_database_uses_multi_az_and_longer_backup_retention(self) -> None:
        app = App()
        stack = PlatformStack(
            app,
            "PlatformProdTest",
            config=StageConfig.for_name("prod"),
            env=Environment(region="sa-east-1"),
        )
        production_template = Template.from_stack(stack)

        production_template.has_resource_properties(
            "AWS::RDS::DBInstance",
            {
                "EngineVersion": "17.6",
                "MultiAZ": True,
                "BackupRetentionPeriod": 30,
                "DeletionProtection": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
