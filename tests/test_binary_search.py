
from unittest import TestCase

from theia.naivestore import binary_search, DataFile

class TestBinarySearch(TestCase):
  
  def test_binary_search_found(self):
    df = [DataFile('a',5,7),DataFile('b',8,12),DataFile('c',13,13.01),DataFile('d',14,15),DataFile('e',15.0001,20)]
    
    assert binary_search(df, 9) == 1
    assert binary_search(df, 13.005) == 2
    assert binary_search(df, 5.00001) == 0
    assert binary_search(df, 19.9) == 4
  
  def test_edge_cases(self):
    df = [DataFile('a',1,7)]
    assert binary_search(df, 3) == 0
    assert binary_search(df, 0) is None
    assert binary_search(df, 8) is None
    
    df = [DataFile('a',1,3), DataFile('b', 4, 5)]
    
    assert binary_search(df, 2) == 0
    assert binary_search(df, 4.5) == 1
    
    assert binary_search([], 3) is None
    
    assert binary_search(df, 3) == 0
    assert binary_search(df, 1) == 0
    
    
    
