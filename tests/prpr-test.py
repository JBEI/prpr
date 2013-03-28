import unittest

import prpr

class TestServer(unittest.TestCase):
    def testPRPRDatabase(self):
        db = prpr.DatabaseHandler.db('SELECT MIN(ExpID) from Experiments')
        expID = db[0][0]
        self.assertEqual(expID, 0)
        

if __name__ == '__main__':
    unittest.main()