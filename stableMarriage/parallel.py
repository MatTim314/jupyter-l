import multiprocessing
import time
import math

def cpu_intensive_task():
    start_time = time.time()
    # Run the task for approximately 60 seconds
    while time.time() - start_time < 60:
        # Perform a CPU-intensive calculation
        for _ in range(1000000):
            math.sqrt(12345.6789)

if __name__ == '__main__':
    # Get the number of available CPU cores
    num_cores = multiprocessing.cpu_count()
    print(f'Using {num_cores} cores')

    # Create a process for each core
    processes = []
    for _ in range(num_cores):
        process = multiprocessing.Process(target=cpu_intensive_task)
        processes.append(process)

    # Start all processes
    for process in processes:
        process.start()

    # Wait for all processes to finish
    for process in processes:
        process.join()

    print('All processes finished')

