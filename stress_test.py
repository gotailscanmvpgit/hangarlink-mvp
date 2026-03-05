import concurrent.futures
import requests
import time
import sys

# Target URL for the stress test
URL = "https://www.hangarlinks.com/"
# Simulating 1000 users accessing the site
TOTAL_REQUESTS = 1000
# Number of concurrent users/threads hitting the site at the exact same moment
CONCURRENT_USERS = 50

def fetch_url(url):
    start_time = time.time()
    try:
        response = requests.get(url, timeout=15)
        end_time = time.time()
        return response.status_code, end_time - start_time
    except requests.exceptions.RequestException as e:
        return 0, 0

def stress_test():
    print(f"Starting stress test on {URL}")
    print(f"Total Requests: {TOTAL_REQUESTS}, Concurrent Nodes: {CONCURRENT_USERS}")
    print("Sending traffic...\n")
    
    start_time = time.time()
    
    status_counts = {}
    response_times = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = [executor.submit(fetch_url, URL) for _ in range(TOTAL_REQUESTS)]
        
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            status, duration = future.result()
            
            if status != 0:
                status_counts[status] = status_counts.get(status, 0) + 1
                response_times.append(duration)
            else:
                status_counts['Timeout/Error'] = status_counts.get('Timeout/Error', 0) + 1
            
            if (i + 1) % 200 == 0:
                print(f"Completed {i + 1}/{TOTAL_REQUESTS} requests...")
                
    total_time = time.time() - start_time
    
    print("\n==========================================")
    print("          STRESS TEST RESULTS             ")
    print("==========================================")
    print(f"Total time elapsed: {total_time:.2f} seconds")
    print(f"Requests per second (RPS): {TOTAL_REQUESTS / total_time:.2f}")
    
    print("\n--- Status Codes ---")
    for status, count in status_counts.items():
        print(f"  HTTP {status}: {count}")
        
    if response_times:
        print("\n--- Response Times ---")
        print(f"  Fastest: {min(response_times):.3f} seconds")
        print(f"  Slowest: {max(response_times):.3f} seconds")
        print(f"  Average: {sum(response_times) / len(response_times):.3f} seconds")
    print("==========================================")

if __name__ == "__main__":
    stress_test()
