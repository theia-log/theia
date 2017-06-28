from theia.collector import Collector
from theia.naivestore import NaiveEventStore

collector = Collector(store=NaiveEventStore('./test'), port=8765)


collector.run()
