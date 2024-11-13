import boto3
from botocore.exceptions import ClientError

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Get AWS Secrets Manager secret"

    def add_arguments(self, parser):
        parser.add_argument("secret_name", type=str)
        parser.add_argument("--region_name", type=str, default="us-east-1")

    def handle(self, *args, **options):
        secret_name = options["secret_name"]
        region_name = options["region_name"]

        self.stdout.write(
            self.style.WARNING(f"Retrieving secret {secret_name} in {region_name}")
        )

        secret = get_secret(secret_name, region_name)

        self.stdout.write(self.style.SUCCESS(f"Secret: {secret}"))


def get_secret(secret_name, region_name):
    """
    Retrieves a secret from AWS Secrets Manager.

    Args:
        secret_name (str): The name of the secret to retrieve.
        region_name (str, optional): The AWS region in which the secret is stored. Defaults to "us-east-1".

    Returns:
        str: The secret value retrieved from AWS Secrets Manager.

    Raises:
        ClientError: If there is an error retrieving the secret.
    """

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise e

    secret = get_secret_value_response["SecretString"]

    return secret
