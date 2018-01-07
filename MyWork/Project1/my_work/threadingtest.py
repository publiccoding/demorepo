# import multiprocessing

# def worker(num):
#     print("worker:",num)
#     return

# if __name__ == '__main__':
#     jobs = []
#     for i in range(5):
#         p = multiprocessing.Process(target=worker, args=(i,))
#         jobs.append(p)
#         p.start()


# from multiprocessing import Pool , current_process, cpu_count

# def f(x):
#     return x*2

# def start_process():
#     print("starting the : ",current_process().name)

# if __name__ == "__main__":
#     input = list(range(10))
#     print("Inputs",input)
#     builtin_output = list(map(f,input))

#     #number of cores use 
#     pool_size = cpu_count()
#     print("Number of process :",pool_size)
#     pool = Pool(processes = pool_size, initializer=start_process)
#     pool_output = pool.map(f,input)

    
#     pool.close()
#     pool.join()

#     print("Pool OUtput", pool_output)
