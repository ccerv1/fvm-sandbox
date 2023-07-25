from datetime import datetime, timezone
from dotenv import load_dotenv
import os
import requests
from time import sleep


# Load the API key from .env file
load_dotenv()
GITHUB_API_KEY = os.getenv('GITHUB_TOKEN')
GITHUB_GRAPHQL_ENDPOINT = 'https://api.github.com/graphql'
SINCE_DATE = datetime(2022, 1, 1, tzinfo=timezone.utc).isoformat()


def get_owner_type(owner):
    query = '''
    query {
        repositoryOwner(login: "%s") {
            __typename
        }
    }
    ''' % owner

    headers = {
        'Authorization': f'Bearer {GITHUB_API_KEY}'
    }

    response = requests.post(GITHUB_GRAPHQL_ENDPOINT, json={'query': query}, headers=headers)
    if response.status_code == 200:
        data = response.json()
        owner_type = data['data']['repositoryOwner']['__typename']
        return owner_type
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def get_commits_info(owner, repo, since_date=SINCE_DATE):
    query = '''
    query ($owner: String!, $repo: String!, $since_date: GitTimestamp!, $afterCursor: String) {
        repository(owner: $owner, name: $repo) {
            ref(qualifiedName: "main") {
                target {
                    ... on Commit {
                        history(since: $since_date, first: 100, after: $afterCursor) {
                            pageInfo {
                                hasNextPage
                                endCursor
                            }
                            edges {
                                node {
                                    author {
                                        name
                                    }
                                    committedDate
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    '''

    headers = {
        'Authorization': f'Bearer {GITHUB_API_KEY}'
    }

    commits_info = []
    after_cursor = None

    while True:
        variables = {
            "owner": owner,
            "repo": repo,
            "since_date": since_date,
            "afterCursor": after_cursor
        }

        response = requests.post(GITHUB_GRAPHQL_ENDPOINT, json={'query': query, 'variables': variables}, headers=headers)

        if response.status_code == 200:
            data = response.json()
            commits_data = data.get('data', {}).get('repository', {}).get('ref', {}).get('target', {}).get('history', {}).get('edges', [])
            commits_info.extend(commits_data)

            page_info = data.get('data', {}).get('repository', {}).get('ref', {}).get('target', {}).get('history', {}).get('pageInfo', {})
            has_next_page = page_info.get('hasNextPage', False)

            if has_next_page:
                after_cursor = page_info.get('endCursor', None)
                #sleep(2)
            else:
                break
        else:
            print(f"Error: {response.status_code} - {response.text}")
            break

    commit_data = []
    for edge in commits_info:
        node = edge['node']
        author = node['author']['name']
        committed_date = node['committedDate']
        committed_date = datetime.fromisoformat(committed_date.replace('Z', '+00:00'))  # Convert to datetime object
        commit_data.append({'author': author, 'committed_date': committed_date})
    
    return commit_data


if __name__ == '__main__':
    owner = "hypercerts-org"
    repo = "hypercerts"
    commits = get_commits_info(owner, repo)
    if commits:
        for commit in commits:
            print(f"Author: {commit['author']}, Date: {commit['committed_date']}")
