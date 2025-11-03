
# APP Runner Service Integration with API Gateway in VPC

Complete guide: [How to Set Up API Gateway as a Front Door for Your AWS App Runner Service in a Private VPC](https://ykhatri.dev/posts/how-to-set-up-api-gateway-as-a-front-door-for-your-aws-app-runner-service-in-a-vpc-a-practical-guide/)

To manually create a virtualenv on MacOS and Linux:

```bash
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```bash
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```bash
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```bash
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```bash
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

* `cdk ls`          list all stacks in the app
* `cdk synth`       emits the synthesized CloudFormation template
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk docs`        open CDK documentation

Enjoy!
