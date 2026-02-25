#!/usr/bin/env python3
# CEO Agent: Orchestrates pharma team, routes to Traction for growth.

from typing import Dict, Any
import sys

class MockDiscoveryAgent:
    def execute(self, query):
        return {'smiles': ['CC(=O)Oc1ccccc1C(=O)O']}  # Aspirin ex

class MockSynthesisAgent:
    def execute(self, query):
        return {'route': '4-step BRICS'}

class TractionAgent:
    def execute(self, query):
        return {'plan': 'Phase 1 demo ready', 'files': ['plan.md', 'demo.py']}

    def package_for_traction(self, results):
        return 'Demo packaged w/ ' + str(results)

class CEOAgent:
    def __init__(self):
        self.sub_agents = {
            'discovery': MockDiscoveryAgent(),
            'synthesis': MockSynthesisAgent(),
            'traction': TractionAgent(),
        }

    def process_query(self, query: str) -> Dict[str, Any]:
        keywords = ['traction', 'pilot', 'demo', 'outreach']
        if any(k in query.lower() for k in keywords):
            return self.sub_agents['traction'].execute(query)
        results = {name: agent.execute(query) for name, agent in self.sub_agents.items() if name != 'traction'}
        return self.sub_agents['traction'].package_for_traction(results)

if __name__ == '__main__':
    query = sys.argv[1] if len(sys.argv) > 1 else 'demo'
    ceo = CEOAgent()
    result = ceo.process_query(query)
    print(result)
