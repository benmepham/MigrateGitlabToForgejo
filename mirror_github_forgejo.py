#!/usr/bin/env python3

import json

import requests

forgejo_url = "https://forgejo/api/v1"

gogs_token='abc'
github_token='123'

s = requests.Session()
project_list = []
# todo: when more than 100 projects, we need to get the next page
res = s.get('https://api.github.com/user/repos?visibility=all&per_page=100', headers={'Authorization':'Bearer %s'%github_token})
assert res.status_code == 200, 'Error when retrieving the projects. The returned html is %s'%res.text
project_list += json.loads(res.text)

created = 0
for i in range(len(project_list)):
    print('\nMirroring project %s'%project_list[i]['full_name'])

    create_mirror = s.post(forgejo_url+'/repos/migrate', data=dict(
        clone_addr=project_list[i]['clone_url'], 
        auth_token=github_token, 
        repo_name=project_list[i]['name'].replace(' ','-'), 
        description=project_list[i]['description'] or "", 
        uid="1", 
        token=gogs_token,
        service="github",
        wiki=True,
        mirror="on",
        private=project_list[i]['private'] or ""
    ))

    if create_mirror.status_code == 409:
        print('Already exists')
    elif create_mirror.status_code != 201:
        print('Could not create because of %s'%json.loads(create_mirror.text)['message'])
    else:
        print('Created successfully')
        created += 1

print('\nEverything finished!')
print('Created %s projects'%created)
