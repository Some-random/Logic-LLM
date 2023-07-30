import json
import sys

d = json.load(open(sys.argv[1]))

for i in range(len(d)):
    problem = d[i]
    print('This is problem: ' + str(i) + ' id is: ' + str(problem["id"]))
    print(problem['context'].replace('.', '\n').replace('\n ', '\n'))
    if len(problem['raw_logic_programs']) > 1:
        print("More than one program generated for this problem")
        exit()
    print(problem['question'])
    print(problem['raw_logic_programs'][0])
    print('--------------------------------')
    
