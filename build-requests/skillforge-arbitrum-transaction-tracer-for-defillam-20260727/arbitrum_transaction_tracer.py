import logging
import json
from typing import Dict, List
from urllib.parse import urljoin
from http.client import HTTPConnection

class ArbitrumTransactionTracer:
    """
    A tool to trace transactions related to known defillama-hack incidents on Arbitrum.

    Args:
    - api_url (str): The URL of the Arbitrum API.
    - incident_ids (List[str]): A list of incident IDs.
    - contract_addresses (List[str]): A list of contract addresses.

    Attributes:
    - transaction_graph (Dict): A dictionary representing the transaction graph.
    """

    def __init__(self, api_url: str, incident_ids: List[str], contract_addresses: List[str]):
        """
        Initializes the ArbitrumTransactionTracer.

        Args:
        - api_url (str): The URL of the Arbitrum API.
        - incident_ids (List[str]): A list of incident IDs.
        - contract_addresses (List[str]): A list of contract addresses.
        """
        self.api_url = api_url
        self.incident_ids = incident_ids
        self.contract_addresses = contract_addresses
        self.transaction_graph = {}

    def fetch_transaction_data(self, transaction_hash: str) -> Dict:
        """
        Fetches transaction data from the Arbitrum API.

        Args:
        - transaction_hash (str): The hash of the transaction.

        Returns:
        - Dict: A dictionary containing the transaction data.
        """
        try:
            connection = HTTPConnection(self.api_url)
            connection.request('GET', f'/transactions/{transaction_hash}')
            response = connection.getresponse()
            if response.status == 200:
                return json.loads(response.read())
            else:
                logging.error(f'Failed to fetch transaction data: {response.status}')
                return {}
        except Exception as e:
            logging.error(f'Error fetching transaction data: {e}')
            return {}

    def build_transaction_graph(self) -> None:
        """
        Builds the transaction graph by fetching transaction data for each incident ID and contract address.
        """
        for incident_id in self.incident_ids:
            self.transaction_graph[incident_id] = []
            # Fetch transaction data for the incident ID
            transaction_data = self.fetch_transaction_data(incident_id)
            if transaction_data:
                self.transaction_graph[incident_id].append(transaction_data)
            else:
                logging.error(f'No transaction data found for incident ID: {incident_id}')

        for contract_address in self.contract_addresses:
            self.transaction_graph[contract_address] = []
            # Fetch transaction data for the contract address
            transaction_data = self.fetch_transaction_data(contract_address)
            if transaction_data:
                self.transaction_graph[contract_address].append(transaction_data)
            else:
                logging.error(f'No transaction data found for contract address: {contract_address}')

    def print_transaction_graph(self) -> None:
        """
        Prints the transaction graph.
        """
        for key, value in self.transaction_graph.items():
            print(f'Transactions for {key}:')
            for transaction in value:
                print(json.dumps(transaction, indent=4))

def main() -> None:
    api_url = 'https://api.arbitrum.io'
    incident_ids = ['incident1', 'incident2']
    contract_addresses = ['0x1234567890', '0x9876543210']
    tracer = ArbitrumTransactionTracer(api_url, incident_ids, contract_addresses)
    tracer.build_transaction_graph()
    tracer.print_transaction_graph()

if __name__ == '__main__':
    main()