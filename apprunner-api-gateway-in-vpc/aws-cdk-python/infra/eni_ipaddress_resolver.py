from typing import Sequence

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import custom_resources as cr
from constructs import Construct

__author__ = "Yougeshwar Khatri"
__license__ = "MIT"
__website__ = "https://ykhatri.dev"


class EniIpAddressResolver(cr.AwsCustomResource):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        network_interface_ids: Sequence[str],
    ) -> None:

        self.output_paths = [
            f"NetworkInterfaces.{i}.PrivateIpAddress"
            for i in range(len(network_interface_ids))
        ]

        aws_sdk_call = cr.AwsSdkCall(
            service="EC2",
            action="describeNetworkInterfaces",
            parameters={
                "NetworkInterfaceIds": network_interface_ids,
            },
            physical_resource_id=cr.PhysicalResourceId.of("EniIPLookup"),
            output_paths=self.output_paths,
        )

        cr_policy = cr.AwsCustomResourcePolicy.from_statements([
            iam.PolicyStatement(
                actions=["ec2:DescribeNetworkInterfaces"],
                resources=["*"],
            )
        ])

        super().__init__(scope, id, on_update=aws_sdk_call, policy=cr_policy,
                         install_latest_aws_sdk=False, timeout=cdk.Duration.minutes(5))

    def get_ip_addresses(self) -> Sequence[str]:
        return [self.get_response_field(path) for path in self.output_paths]
