import os
import json
from datetime import datetime
from testing_outage import check_outage_logs

print("="*60)
print("TESTING OUTAGE LOGS WITH BOTH DATE FORMATS")
print("="*60)

print("\nTest 1 - Lucknow, Standard format (YYYY-MM-DD HH:MM:SS):")
result1 = check_outage_logs("2024-06-01 02:18:00", "Lucknow")
print(result1)

print("\nTest 2 - Lucknow, ISO format (YYYY-MM-DDTHH:MM:SSZ):")
result2 = check_outage_logs("2024-06-01T02:18:00Z", "Lucknow")
print(result2)

print("\nTest 3 - Chennai, Standard format (YYYY-MM-DD HH:MM:SS):")
result3 = check_outage_logs("2024-06-01 13:25:00", "Chennai")
print(result3)

print("\nTest 4 - Chennai, ISO format (YYYY-MM-DDTHH:MM:SSZ):")
result4 = check_outage_logs("2024-06-01T13:25:00Z", "Chennai")
print(result4)

print("\nTest 5 - Non-matching region (should return no outages):")
result5 = check_outage_logs("2024-06-01 02:18:00", "Mumbai")
print(result5)

print("\n" + "="*60)
print("VERIFICATION:")
print("="*60)
print(f"Test 1 & 2 identical: {result1 == result2}")
print(f"Test 3 & 4 identical: {result3 == result4}")
print(f"Both found outages: {('hardware failure' in result1) and ('power outage' in result3)}")
print("="*60)
