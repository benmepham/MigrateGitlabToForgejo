#!/usr/bin/env python3

import argparse
import json
import os
import subprocess

import requests

parser = argparse.ArgumentParser()
parser.add_argument('--source_namespace', 
                    help='The namespace in github as it appears in URLs. For example, given the repository address http://mygithub.com/harry/my-awesome-repo.git, it shows that this repository lies within my personal namespace "harry". Hence I would pass harry as parameter.',
                    required=True)
parser.add_argument('--add_to_private',default=None, action='store_true',help='If you want to add the repositories under your own name, ie. not in any organisation, use this flag.')
parser.add_argument('--add_to_organization',default=None, metavar='organization_name', help='If you want to add all the repositories to an exisiting organisation, please pass the name to this parameter. Organizations correspond to groups in github. The name can be taken from the URL, for example, if your organization is http://mygogs-repo.com/org/my-awesome-organisation/dashboard then pass my-awesome-organisation here')
parser.add_argument('--source_repo', 
                    help='URL to your github repo in the format http://mygithub.com/',
                    required=True)
parser.add_argument('--target_repo', 
                    help='URL to your gogs / gitea repo in the format http://mygogs.com/',
                    required=True)
parser.add_argument('--no_confirm', 
                    help='Skip user confirmation of each single step',
                    action='store_true')
parser.add_argument('--skip_existing', 
                    help='Skip repositories that already exist on remote without asking the user',
                    action='store_true')

args = parser.parse_args()

assert args.add_to_private or args.add_to_organization is not None, 'Please set either add_to_private or provide a target oranization name!'

print('In the following, we will check out all repositories from ')
print('the namespace %s to the current directory and push it to '%args.source_namespace)
if args.add_to_private:
    print('your personal account', end='')
else:
    print('to the organisation %s'%args.add_to_organization, end='')
print(' as private repositories.')

if not args.no_confirm:
    input('Hit any key to continue!')

gogs_url = args.target_repo + "/api/v1"
github_url = args.source_repo #+ '/api/v4'

gogs_token='abc'

github_token='abc'



print('Getting existing projects from namespace %s...'%args.source_namespace)
s = requests.Session()
project_list = []

res = s.get('https://api.github.com/user/repos?visibility=all&per_page=100', headers={'Authorization':'Bearer %s'%github_token})
assert res.status_code == 200, 'Error when retrieving the projects. The returned html is %s'%res.text
print('Got %s projects'%len(json.loads(res.text)))
project_list += json.loads(res.text)


print('\n\nFinished preparations. We are about to migrate the following projects:')

print('\n'.join([p['full_name'] for p in project_list]))

if not args.no_confirm:
    if 'y' != input('Do you want to continue? (please answer y or no) '):
        print('\nYou decided to cancel...')
        exit(1)


for i in range(len(project_list)):
    src_name = project_list[i]['name']
    src_id = project_list[i]['id']
    src_url = project_list[i]['clone_url']
    src_description = project_list[i]['description']
    dst_name = src_name.replace(' ','-')

    print('\n\nMigrating project %s to project %s now.'%(src_url,dst_name))

    if not args.no_confirm:
        if 'y' != input('Do you want to continue? (please answer y or n) '):
            print('\nYou decided to cancel...')
            continue

    # Create repo 
    if args.add_to_private:
        create_repo = s.post(gogs_url+'/user/repos', data=dict(token=gogs_token, name=dst_name, private=True))
    elif args.add_to_organization:
        create_repo = s.post(gogs_url+'/org/%s/repos'%args.add_to_organization, 
                            data=dict(token=gogs_token, name=dst_name, private=True, description=src_description))
    if create_repo.status_code != 201:
        print('Could not create repo %s because of %s'%(src_name,json.loads(create_repo.text)['message']))
        if args.skip_existing:
            print('\nSkipped')
        else:
            if 'y' != input('Do you want to skip this repo and continue with the next? (please answer y or no) '):
                print('\nYou decided to cancel...')
                exit(1)
        continue
    
    dst_info = json.loads(create_repo.text)

    dst_url = dst_info['clone_url']
    # Git pull and push
    subprocess.check_call(['git','clone','--bare',src_url])
    os.chdir(src_url.split('/')[-1])
    branches=subprocess.check_output(['git','branch','-a'])
    if len(branches) == 0:
        print('\n\nThis repository is empty - skipping push')
    else:
        subprocess.check_call(['git','push','--mirror',dst_url])
    os.chdir('..')
    subprocess.check_call(['rm','-rf',src_url.split('/')[-1]]) 

    print('\n\nFinished migration. New project URL is %s'%dst_info['html_url'])
    print('Please open the URL and check if everything is fine.')

    if not args.no_confirm:
        if 'y' != input('Do you want to DELETE the project on github? (please answer y or no) '):
                continue
        archive_repo = s.delete('https://api.github.com/repos/%s/%s'%('benmepham',src_name), headers={'Authorization':'Bearer %s'%github_token})
        if archive_repo.status_code != 204:
            print('Could not delete repo %s because of %s'%(src_name,json.loads(archive_repo.text)['message']))
        else:
            print('Deleted repo %s'%src_name)
    
print('\n\nEverything finished!\n')
