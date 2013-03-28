import unittest

import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

import prpr

class TestServer(unittest.TestCase):
    def testPRPRDatabase(self):
        db = prpr.DatabaseHandler.db('SELECT MIN(ExpID) from Experiments')
        expID = db[0][0]
        self.assertEqual(expID, 0)
        

if __name__ == '__main__':
    unittest.main()