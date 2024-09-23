import numpy as np
import pandas as pd
import os

class contrans:
    def __init__(self):
        """
        Initialize the contrans object.

        The mypassword attribute is set to the value of the MYPASSWORD
        environment variable.

        """
        self.mypassword = os.getenv('mypassword')
    
    def get_votes(self):
            url = 'https://voteview.com/static/data/out/votes/H118_votes.csv'
            votes = pd.read_csv(url)
            return votes
    
    def get_ideology(self):
            url = 'https://voteview.com/static/data/out/members/H118_members.csv'
            members = pd.read_csv(url)
            return members