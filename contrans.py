import numpy as np
import pandas as pd
import os
import dotenv
import requests
import json
from bs4 import BeautifulSoup
import psycopg
import sqlite3
from sqlalchemy import create_engine

dotenv.load_dotenv()

class contrans:
    def __init__(self):
        """
        Initialize the contrans object.

        The mypassword attribute is set to the value of the MYPASSWORD
        environment variable.

        """
        self.mypassword = os.getenv('mypassword')
        self.congresskey = os.getenv('congresskey')
        self.newskey = os.getenv('newskey')
        self.POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
        self.MONGO_INITDB_ROOT_USERNAME = os.getenv('MONGO_INITDB_ROOT_USERNAME')
        self.MONGO_INITDB_ROOT_PASSWORD = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
        self.us_state_to_abbrev = {
                        "Alabama": "AL","Alaska": "AK","Arizona": "AZ","Arkansas": "AR",
                        "California": "CA","Colorado": "CO","Connecticut": "CT","Delaware": "DE",
                        "Florida": "FL","Georgia": "GA","Hawaii": "HI",
                        "Idaho": "ID","Illinois": "IL","Indiana": "IN","Iowa": "IA",
                        "Kansas": "KS","Kentucky": "KY","Louisiana": "LA",
                        "Maine": "ME","Maryland": "MD","Massachusetts": "MA",
                        "Michigan": "MI","Minnesota": "MN","Mississippi": "MS",
                        "Missouri": "MO","Montana": "MT","Nebraska": "NE",
                        "Nevada": "NV","New Hampshire": "NH","New Jersey": "NJ",
                        "New Mexico": "NM","New York": "NY","North Carolina": "NC",
                        "North Dakota": "ND","Ohio": "OH","Oklahoma": "OK",
                        "Oregon": "OR","Pennsylvania": "PA","Rhode Island": "RI",
                        "South Carolina": "SC","South Dakota": "SD","Tennessee": "TN",
                        "Texas": "TX","Utah": "UT","Vermont": "VT",
                        "Virginia": "VA","Washington": "WA","West Virginia": "WV",
                        "Wisconsin": "WI","Wyoming": "WY","District of Columbia": "DC",
                        "American Samoa": "AS","Guam": "GU","Northern Mariana Islands": "MP",
                        "Puerto Rico": "PR","United States Minor Outlying Islands": "UM",
                        "Virgin Islands": "VI"
                        }
    
    def get_votes(self):
            url = 'https://voteview.com/static/data/out/votes/H118_votes.csv'
            votes = pd.read_csv(url)
            return votes
    
    def get_ideology(self):
            url = 'https://voteview.com/static/data/out/members/H118_members.csv'
            members = pd.read_csv(url)
            return members
    
    
    def get_useragent(self):
        url = 'https://httpbin.org/user-agent'
        r = requests.get(url)
        useragent = json.loads(r.text)['user-agent']
        return useragent
    
    def make_headers(self,  
                     email='fvq3xv@virginia.edu'):
            useragent=self.get_useragent()
            headers = {
                'User-Agent': useragent,
                'From': email
            }
            return headers
        
    def get_bioguideIDs(self, congress=118):
                params = {'api_key': self.congresskey,
                          'limit': 1} 
                headers = self.make_headers()
                root = 'https://api.congress.gov/v3'
                endpoint = f'/member/congress/{congress}'
                r = requests.get(root + endpoint,
                                 params=params,
                                 headers=headers)
                totalrecords = r.json()['pagination']['count']
                
                params['limit'] = 250
                j = 0
                bio_df = pd.DataFrame()
                while j < totalrecords:
                        params['offset'] = j
                        r = requests.get(root + endpoint,
                                         params=params,
                                         headers=headers)
                        records = pd.json_normalize(r.json()['members'])
                        bio_df = pd.concat([bio_df, records])
                        j = j + 250

                #bio_df = bio_df[['name', 'state', 'district', 'partyName', 'bioguideId']]
                return bio_df
            
    def get_bioguide(self, name, state=None, district=None):
                members = self.get_bioguideIDs()# replace with SQL query
                
                members['name'] = members['name'].str.lower().str.strip()
                name = name.lower().strip()
                
                tokeep = [name in x for x in members['name']]
                members = members[tokeep]
                
                if state is not None:
                    members = members.query('state == @state')
                if district is not None:
                    members = members.query('district == @district')
                
                return members.reset_index(drop=True)
    
    def get_sponsoredlegislation(self, bioguideId):

                params = {'api_key': self.congresskey,
                          'limit': 1} 
                headers = self.make_headers()
                root = 'https://api.congress.gov/v3'
                endpoint = f'/member/{bioguideId}/sponsored-legislation'
                r = requests.get(root + endpoint,
                                 params=params,
                                 headers=headers)
                totalrecords = r.json()['pagination']['count']
                
                params['limit'] = 250
                j = 0
                bills_list = []
                while j < totalrecords:
                        params['offset'] = j
                        r = requests.get(root + endpoint,
                                         params=params,
                                         headers=headers)
                        records = r.json()['sponsoredLegislation']
                        bills_list = bills_list + records
                        j = j + 250
        
                return bills_list
            
    def get_billdata(self, billurl):
        r = requests.get(billurl,
                     params={'api_key': self.congresskey})
        bill_json = json.loads(r.text)
        texturl = bill_json['bill']['textVersions']['url']
        r = requests.get(texturl,
                         params={'api_key': self.congresskey})
        toscrape = json.loads(r.text)['textVersions'][0]['formats'][0]['url']
        r = requests.get(toscrape)
        mysoup = BeautifulSoup(r.text, 'html.parser')
        billtext =  mysoup.text
        bill_json['bill_text'] = billtext
        return bill_json
    
    def make_cand_table(self, members):
                # members is output of get_terms()
                # members = self.get_bioguideIDs()
                replace_map = {'Republican': 'R','Democratic': 'D','Independent': 'I'}
                members['partyletter'] = members['partyName'].replace(replace_map)
                members['state'] = members['state'].replace(self.us_state_to_abbrev)
                members['district'] = members['district'].fillna(0)
                members['district'] = members['district'].astype('int').astype('str')
                members['district'] = ['0' + x if len(x) == 1 else x for x in members['district']]
                members['district'] = [x.replace('00', 'S') for x in members['district']]
                members['DistIDRunFor'] = members['state']+members['district']
                members['lastname']= [x.split(',')[0] for x in members['name']]
                members['firstname']= [x.split(',')[1] for x in members['name']]
                members['name2'] = [ y.strip() + ' (' + z.strip() + ')' 
                                for y, z in 
                                zip(members['lastname'], members['partyletter'])]
                
                cands = pd.read_csv('data/cands22.txt', quotechar="|", header=None)
                cands.columns = ['Cycle', 'FECCandID', 'CID','FirstLastP',
                                'Party','DistIDRunFor','DistIDCurr',
                                'CurrCand','CycleCand','CRPICO','RecipCode','NoPacs']
                cands['DistIDRunFor'] = [x.replace('S0', 'S') for x in cands['DistIDRunFor']]
                cands['DistIDRunFor'] = [x.replace('S1', 'S') for x in cands['DistIDRunFor']]
                cands['DistIDRunFor'] = [x.replace('S2', 'S') for x in cands['DistIDRunFor']]
                cands['name2'] = [' '.join(x.split(' ')[-2:]) for x in cands['FirstLastP']]
                cands = cands[['CID', 'name2', 'DistIDRunFor']].drop_duplicates(subset=['name2', 'DistIDRunFor'])
                crosswalk = pd.merge(members, cands, 
                     left_on=['name2', 'DistIDRunFor'],
                     right_on=['name2', 'DistIDRunFor'],
                     how = 'left')
                return crosswalk
            
    def terms_df(self, members):
                termsDF = pd.DataFrame()
                for index, row in members.iterrows():
                        bioguide_id = row['bioguideId']
                        terms = row['terms.item']
                        df = pd.DataFrame.from_records(terms)
                        df['bioguideId'] = bioguide_id
                        termsDF = pd.concat([termsDF, df])
                members = members.drop('terms.item', axis=1)
                return termsDF, members
    
    ### Connect to Databases
            
    def connect_to_postgres(self, pw, user='postgres',
                            host='localhost', port=5432,
                            create_contrans=False):
        dbserver = psycopg.connect(
            user=user,
            password=pw,
            host=host,
            port=port
        )
        dbserver.autocommit = True
        if create_contrans:
            cursor = dbserver.cursor()
            cursor.execute('DROP DATABASE IF EXISTS contrans')
            cursor.execute('CREATE DATABASE contrans')
        engine = create_engine(f'postgresql+psycopg://{user}:{pw}@{host}:{port}/contrans')
        return dbserver, engine
        
    
    ### Methods for building the 3NF relational DB tables

    def make_members_df(self, members, ideology, engine):
                '''
                members should be the output of get_bioguideIDs(), 
                with terms removed by get_terms(),
                augmented with contributions by make_cand_table().
                ideology should be the output of get_ideology().
                '''
                members_df = pd.merge(members, ideology, 
                                      left_on='bioguideId', 
                                      right_on='bioguide_id',
                                      how='left')
                # dbserver, engine = self.connect_to_postgres(self.POSTGRES_PASSWORD)
                members_df.columns = members_df.columns.str.lower()
                members_df.columns = members_df.columns.str.replace('.', '_')
                members_df.to_sql('members', con=engine, index=False, chunksize=1000, if_exists='replace')
        
    def make_terms_df(self, terms, engine):
                terms.columns = terms.columns.str.lower()
                terms.to_sql('terms', con=engine, index=False, chunksize=1000, if_exists='replace')
        
    def make_votes_df(self, votes, engine):
                votes.columns = votes.columns.str.lower()
                votes.to_sql('votes', con=engine, index=False, chunksize=1000, if_exists='replace')
        
    def make_agreement_df(self):
                return self
            
    def dbml_helper(self, data):
                dt = data.dtypes.reset_index().rename({0:'dtype'}, axis=1)
                replace_map = {'object': 'varchar',
                                'int64': 'int',
                                'float64': 'float'}
                dt['dtype'] = dt['dtype'].replace(replace_map)
                return dt.to_string(index=False, header=False)
            
    