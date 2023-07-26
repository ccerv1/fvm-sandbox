from datetime import datetime, timezone
from dotenv import load_dotenv
import os
import requests

# Load the API key from .env file
load_dotenv()
GITHUB_API_KEY = os.getenv('GITHUB_TOKEN')
GITHUB_GRAPHQL_ENDPOINT = 'https://api.github.com/graphql'
SINCE_DATE = datetime(2022, 1, 1, tzinfo=timezone.utc).isoformat()


def make_graphql_request(query, variables=None):
    headers = {
        'Authorization': f'Bearer {GITHUB_API_KEY}'
    }

    response = requests.post(GITHUB_GRAPHQL_ENDPOINT, json={'query': query, 'variables': variables}, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('data', {})
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def get_owner_type(owner):
    query = '''
    query ($owner: String!) {
        repositoryOwner(login: $owner) {
            __typename
        }
    }
    '''

    data = make_graphql_request(query, variables={"owner": owner})
    if data:
        owner_type = data.get('repositoryOwner', {}).get('__typename')
        return owner_type
    else:
        return f"Could not find valid owner at https://github.com/{owner}"


def get_repo_stats(owner, repo):
    GITHUB_API_BASE_URL = 'https://api.github.com/repos'
    response = requests.get(f'{GITHUB_API_BASE_URL}/{owner}/{repo}')

    result = {"contributors": [], "last_update": None, "stars": 0}

    if response.status_code == 200:
        data = response.json()
        result["last_update"] = data.get('pushed_at')
        result["stars"] = data.get('stargazers_count')
        contributors_url = data.get('contributors_url')
        contributors_response = requests.get(contributors_url)
        if contributors_response.status_code == 200:
            contributors_data = contributors_response.json()
            result["contributors"] = [contributor['login'] for contributor in contributors_data]
    else:
        print(f"Error: {response.status_code} - {response.text}")

    return result


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
                                        user {
                                            login
                                        }
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

    commits_info = []
    after_cursor = None

    while True:
        variables = {
            "owner": owner,
            "repo": repo,
            "since_date": since_date,
            "afterCursor": after_cursor
        }

        data = make_graphql_request(query, variables)
        if data:
            ref = data.get('repository', {}).get('ref', {})
            commits_data = ref.get('target', {}).get('history', {}).get('edges', [])
            commits_info.extend(commits_data)

            page_info = ref.get('target', {}).get('history', {}).get('pageInfo', {})
            has_next_page = page_info.get('hasNextPage', False)

            if has_next_page:
                after_cursor = page_info.get('endCursor', None)
                # sleep(2)  # Introduce a delay to avoid rate limits
            else:
                break
        else:
            break

    # Extract the author's login and commit date
    commit_data = []
    for edge in commits_info:
        node = edge['node']
        author_login = node['author']['user']['login'] if node['author'] and node['author']['user'] else 'Unknown'
        committed_date = node['committedDate']
        committed_date = datetime.fromisoformat(committed_date.replace('Z', '+00:00'))  # Convert to datetime object
        commit_data.append({'author_login': author_login, 'committed_date': committed_date, 'repo': repo})

    return commit_data


def get_all_repos(owner):
    query = '''
    query ($owner: String!, $afterCursor: String) {
        user(login: $owner) {
            repositories(first: 100, after: $afterCursor, isFork: false) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                edges {
                    node {
                        name
                    }
                }
            }
        }
    }
    '''

    all_repos = []
    after_cursor = None

    while True:
        variables = {
            "owner": owner,
            "afterCursor": after_cursor
        }

        data = make_graphql_request(query, variables)
        if data:
            repos = data.get('user', {}).get('repositories', {}).get('edges', [])

            for repo in repos:
                repo_name = repo['node']['name']
                all_repos.append(repo_name)

            page_info = data.get('user', {}).get('repositories', {}).get('pageInfo', {})
            has_next_page = page_info.get('hasNextPage', False)

            if has_next_page:
                after_cursor = page_info.get('endCursor', None)
            else:
                break
        else:
            break

    return all_repos


if __name__ == '__main__':
    owner = "hypercerts-org"
    repo = "hypercerts"
    # print(get_all_repos(owner))
    # commits = get_commits_info(owner, repo)
    commits = get_commits_info(owner, repo)
    if commits:
        for commit in commits:
            print(f"User: {commit['author_login']}, Date: {commit['committed_date']}")
