"""
Mock data generator for test cases
"""
from faker import Faker
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class MockDataGenerator:
    """Generate realistic mock data for testing"""
    
    def __init__(self, locale: str = "en_US"):
        self.faker = Faker(locale)
    
    def generate_user_credentials(self) -> Dict[str, str]:
        """Generate user login credentials"""
        return {
            "username": self.faker.email(),
            "password": self.faker.password(length=12, special_chars=True),
            "full_name": self.faker.name()
        }
    
    def generate_customer_data(self) -> Dict[str, Any]:
        """Generate customer data"""
        return {
            "customer_id": self.faker.uuid4(),
            "first_name": self.faker.first_name(),
            "last_name": self.faker.last_name(),
            "email": self.faker.email(),
            "phone": self.faker.phone_number(),
            "company": self.faker.company(),
            "address": self.faker.address(),
            "date_of_birth": self.faker.date_of_birth().isoformat()
        }
    
    def generate_financial_data(self) -> Dict[str, Any]:
        """Generate financial data"""
        return {
            "account_number": self.faker.bban(),
            "amount": round(self.faker.random.uniform(100, 10000), 2),
            "transaction_date": self.faker.date_this_year().isoformat(),
            "transaction_id": self.faker.uuid4(),
            "status": self.faker.random_element(["PENDING", "COMPLETED", "FAILED"])
        }
    
    def generate_product_data(self) -> Dict[str, Any]:
        """Generate product data"""
        return {
            "product_id": self.faker.uuid4(),
            "product_name": self.faker.word(),
            "sku": self.faker.ean13(),
            "price": round(self.faker.random.uniform(10, 1000), 2),
            "stock_quantity": self.faker.random_int(min=0, max=1000),
            "category": self.faker.word()
        }
    
    def generate_test_data_for_scenario(self, scenario: str) -> Dict[str, Any]:
        """
        Generate test data based on scenario type
        
        Args:
            scenario: Test scenario name
            
        Returns:
            Dictionary with mock data
        """
        scenario_lower = scenario.lower()
        
        if "login" in scenario_lower or "auth" in scenario_lower:
            return self.generate_user_credentials()
        elif "customer" in scenario_lower:
            return self.generate_customer_data()
        elif "finance" in scenario_lower or "transaction" in scenario_lower:
            return self.generate_financial_data()
        elif "product" in scenario_lower:
            return self.generate_product_data()
        else:
            # Generic data generation
            return {
                "id": self.faker.uuid4(),
                "name": self.faker.word(),
                "email": self.faker.email(),
                "timestamp": self.faker.iso8601()
            }
    
    def generate_bulk_data(self, scenario: str, count: int = 5) -> List[Dict[str, Any]]:
        """Generate multiple data records"""
        return [self.generate_test_data_for_scenario(scenario) for _ in range(count)]
