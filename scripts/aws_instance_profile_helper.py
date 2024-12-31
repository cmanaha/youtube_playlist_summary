#!/usr/bin/env python3

import boto3
import argparse
from rich.console import Console
from rich.table import Table

console = Console()

# Constants
INFERENCE_PROFILE_NAME = "YoutubePlaylistAnalyzer-123120241249"

def create_nova_inference_profile(
    profile_name: str = INFERENCE_PROFILE_NAME,
    region: str = "us-east-1",
) -> None:
    """Create an inference profile for Nova Lite model."""
    try:
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock', region_name=region)
        
        # Check if profile already exists
        try:
            response = bedrock.get_inference_profile(
                inferenceProfileIdentifier=profile_name
            )
            console.log(f"[yellow]Inference profile already exists: {profile_name}[/yellow]")
            return
        except bedrock.exceptions.ResourceNotFoundException:
            console.log(f"[green]Creating new inference profile: {profile_name}[/green]")
        
        # Create the inference profile
        response = bedrock.create_inference_profile(
            inferenceProfileName=profile_name,
            description="Inference profile for Nova Lite model",
            modelSource={
                'copyFrom': f"arn:aws:bedrock:{region}::foundation-model/amazon.nova-lite-v1:0"
            },
            tags=[{
                "key": "AppName",
                "value": "YoutubePlaylistSummarizer",
            }]
        )

        print(f"Response: {response}")
        
        profile_arn = response['inferenceProfileArn']
        console.log(f"[green]Successfully created inference profile[/green] {response['status']}")
        console.log(f"[blue]ARN: {profile_arn}[/blue]")
    except Exception as e:
        console.log(f"[red]Error creating inference profile: {str(e)}[/red]")
        raise

def list_inference_profiles(region: str = "us-east-1") -> None:
    """List all inference profiles in the region."""
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        
        # Create a table for display
        table = Table(
            title=f"Inference Profiles in {region}",
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("Name", style="cyan")
        table.add_column("inferenceProfileId", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Model", style="green")
        table.add_column("Created", style="yellow")
        table.add_column("ARN", style="white")
        
        try:
            paginator = bedrock.get_paginator('list_inference_profiles')
            profile_count = 0
            
            for page in paginator.paginate():
                for profile in page['inferenceProfileSummaries']:
                    profile_count += 1
            
                    table.add_row(
                        profile['inferenceProfileName'],
                        profile['inferenceProfileId'],
                        profile['status'],
                        '\n'.join(v['modelArn'] for v in profile['models']),
                        profile['createdAt'].strftime('%Y-%m-%d %H:%M:%S'),
                        profile['inferenceProfileArn']
                    )

            app_profiles = paginator.paginate(typeEquals='APPLICATION')
            for page in app_profiles:
                for profile in page['inferenceProfileSummaries']:
                    profile_count += 1

                    
                    table.add_row(
                        profile['inferenceProfileName'],
                        profile['inferenceProfileId'],
                        profile['status'],
                        '\n'.join(v['modelArn'] for v in profile['models']),
                        profile['createdAt'].strftime('%Y-%m-%d %H:%M:%S'),
                        profile['inferenceProfileArn']
                    )                       


            if profile_count == 0:
                console.log("[yellow]No inference profiles found[/yellow]")
            else:
                console.print(table)
                
        except bedrock.exceptions.ResourceNotFoundException:
            console.log("[yellow]No inference profiles found[/yellow]")
            
    except Exception as e:
        console.log(f"[red]Error listing inference profiles: {str(e)}[/red]")
        raise

def delete_nova_inference_profile(
    profile_name: str = INFERENCE_PROFILE_NAME,
    region: str = "us-east-1"
) -> None:
    """Delete all inference profiles matching the given name."""
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        profiles_deleted = 0
        
        try:
            # List all inference profiles
            paginator = bedrock.get_paginator('list_inference_profiles')
            matching_profiles = []
            
            # Check application profiles
            app_profiles = paginator.paginate(typeEquals='APPLICATION')
            for page in app_profiles:
                for profile in page['inferenceProfileSummaries']:
                    if profile['inferenceProfileName'] == profile_name:
                        matching_profiles.append(profile['inferenceProfileId'])
            
            if not matching_profiles:
                console.log(f"[yellow]No inference profiles found with name: {profile_name}[/yellow]")
                return
            
            # Delete each matching profile
            for profile_id in matching_profiles:
                try:
                    bedrock.delete_inference_profile(
                        inferenceProfileIdentifier=profile_id
                    )
                    profiles_deleted += 1
                    console.log(f"[green]Successfully deleted inference profile ID: {profile_id}[/green]")
                except Exception as e:
                    console.log(f"[red]Error deleting profile {profile_id}: {str(e)}[/red]")
            
            console.log(f"[green]Deleted {profiles_deleted} inference profile(s) named '{profile_name}'[/green]")
                
        except bedrock.exceptions.ResourceNotFoundException:
            console.log(f"[yellow]No inference profiles found with name: {profile_name}[/yellow]")
            
    except Exception as e:
        console.log(f"[red]Error in delete operation: {str(e)}[/red]")
        raise


def main():
    parser = argparse.ArgumentParser(description='Manage Nova Lite inference profile')
    parser.add_argument('--action', choices=['create', 'delete', 'list'], default='list',
                      help='Action to perform (create, delete, or list profiles)')
    parser.add_argument('--region', default='us-east-1',
                      help='AWS region (default: us-east-1)')
    parser.add_argument('--profile-name', default=INFERENCE_PROFILE_NAME,
                      help='Name of the inference profile')
    
    args = parser.parse_args()
    
    if args.action == 'create':
        create_nova_inference_profile(
            profile_name=args.profile_name,
            region=args.region,
        )
    elif args.action == 'list':
        list_inference_profiles(region=args.region)
    else:
        delete_nova_inference_profile(
            profile_name=args.profile_name,
            region=args.region
        )

if __name__ == "__main__":
    main() 