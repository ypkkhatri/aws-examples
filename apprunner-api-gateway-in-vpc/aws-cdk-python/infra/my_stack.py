import aws_cdk as cdk
from aws_cdk import Stack
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_apprunner as apprunner
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_elasticloadbalancingv2_targets as elbv2targets
from aws_cdk import aws_iam as iam
from constructs import Construct
from eni_ipaddress_resolver import EniIpAddressResolver

__author__ = "Yougeshwar Khatri"
__license__ = "MIT"
__website__ = "https://ykhatri.dev"


class MyStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(
            self, "VPCId",
            vpc_name="my-vpc",
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="my-private-subnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                )
            ],
            nat_gateways=0  # We don't need the NAT gateway
        )

        vpc_private_subnet_ids = [
            subnet.subnet_id for subnet in vpc.private_subnets]

        security_group = ec2.SecurityGroup(
            self, "SecurityGroupId",
            security_group_name="security-group",
            vpc=vpc,
            allow_all_outbound=True,
        )

        security_group_ids = [security_group.security_group_id]

        security_group.add_ingress_rule(
            peer=security_group,
            connection=ec2.Port.all_traffic(),
            description="Allow all traffic within the security group"
        )

        vpc_apprunner_requests_endpoint = ec2.InterfaceVpcEndpoint(
            self, "AppRunnerRequestsEndpointId",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointAwsService.APP_RUNNER_REQUESTS,
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[security_group],
            private_dns_enabled=False,
        )

        vpc_apprunner_requests_endpoint_eni_ids = [cdk.Fn.select(
            i,
            vpc_apprunner_requests_endpoint.vpc_endpoint_network_interface_ids
        ) for i in range(len(vpc_private_subnet_ids))]

        eni_ipaddress_resolver = EniIpAddressResolver(
            self, "EniIpAddressResolverId",
            network_interface_ids=vpc_apprunner_requests_endpoint_eni_ids
        )
        app_runner_vpc_endpoint_ips = eni_ipaddress_resolver.get_ip_addresses()

        nlb_apprunner = elbv2.NetworkLoadBalancer(
            self, "NLBAppRunnerId",
            load_balancer_name="nlb-app-runner",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[security_group],
            internet_facing=False,
            cross_zone_enabled=True,
            enforce_security_group_inbound_rules_on_private_link_traffic=False,
        )

        nlb_network_group = elbv2.NetworkTargetGroup(
            self, "NLBAppRunnerTargetGroupId",
            target_group_name="my-nlb-app-runner-tg",
            vpc=vpc,
            port=443,
            protocol=elbv2.Protocol.TCP,
            target_type=elbv2.TargetType.IP,
            targets=[elbv2targets.IpTarget(
                ip) for ip in app_runner_vpc_endpoint_ips]
        )

        nlb_apprunner.add_listener(
            "NLBAppRunnerListenerId",
            default_target_groups=[nlb_network_group],
            port=443,
            protocol=elbv2.Protocol.TCP
        )

        apprunner_vpc_connector = apprunner.CfnVpcConnector(
            self, "AppRunnerVpcConnectorId",
            vpc_connector_name="my-arvpcconn",
            subnets=vpc_private_subnet_ids,
            security_groups=security_group_ids,
        )

        app_runner_role = iam.Role(
            self,
            "IAMAppRunnerAccessRoleId",
            role_name="my-apprunner-access-role",
            assumed_by=iam.ServicePrincipal("build.apprunner.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryReadOnly")
            ]
        )

        apprunner_backend_api_service = apprunner.CfnService(
            self, "AppRunnerBackendAPIServiceId",
            source_configuration=apprunner.CfnService.SourceConfigurationProperty(
                authentication_configuration=apprunner.CfnService.AuthenticationConfigurationProperty(
                    access_role_arn=app_runner_role.role_arn
                ),
                image_repository=apprunner.CfnService.ImageRepositoryProperty(
                    image_identifier="my-app-image:latest",  # Replace with your ECR image URI
                    image_repository_type="ECR"
                )
            ),
            network_configuration=apprunner.CfnService.NetworkConfigurationProperty(
                ingress_configuration=apprunner.CfnService.IngressConfigurationProperty(
                    is_publicly_accessible=False
                ),
                egress_configuration=apprunner.CfnService.EgressConfigurationProperty(
                    egress_type="VPC",
                    vpc_connector_arn=apprunner_vpc_connector.attr_vpc_connector_arn
                ),
            ),
            health_check_configuration=apprunner.CfnService.HealthCheckConfigurationProperty(
                path="/",
            ),
        )

        apprunner_vpc_ingress_connection = apprunner.CfnVpcIngressConnection(
            self,
            "AppRunnerVpcIngressConnectionId",
            vpc_ingress_connection_name="my-arvpcincon",
            service_arn=apprunner_backend_api_service.attr_service_arn,
            ingress_vpc_configuration=apprunner.CfnVpcIngressConnection.IngressVpcConfigurationProperty(
                vpc_id=vpc.vpc_id,
                vpc_endpoint_id=vpc_apprunner_requests_endpoint.vpc_endpoint_id
            )
        )

        vpc_link = apigateway.VpcLink(
            self, "ApiGatwayVpcLinkId",
            description="VPC Link for App Runner NLB",
            vpc_link_name="my-nlb-vpc-link",
            targets=[nlb_apprunner]
        )

        apigateway_restapi = apigateway.RestApi(
            self, "ApiGatwayOpdRestApiId",
            # ... add remaining properties as needed
        )

        apprunner_integration = apigateway.Integration(
            type=apigateway.IntegrationType.HTTP_PROXY,
            integration_http_method="ANY",
            options=apigateway.IntegrationOptions(
                connection_type=apigateway.ConnectionType.VPC_LINK,
                vpc_link=vpc_link,
                passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_MATCH,
                request_parameters={
                    "integration.request.path.proxy": "method.request.path.proxy"
                },
            ),
            uri=f"https://{apprunner_vpc_ingress_connection.attr_domain_name}" + "/{proxy}",
        )

        restapi_apprunner_app_resource = apigateway_restapi.root.add_proxy(
            any_method=True,
            default_integration=apprunner_integration,
            default_method_options=apigateway.MethodOptions(
                api_key_required=True,  # As its enabled you need to setup the key separately
                request_parameters={
                    "method.request.path.proxy": True
                },
            )
        )

        # Add CORS options to the API Gateway resource to restapi_apprunner_app_resource
