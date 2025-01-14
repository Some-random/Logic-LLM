# generate facts and rules based on the problem description

import json
import os
from tqdm import tqdm
from collections import OrderedDict
from typing import Dict, List, Tuple
from utils import OpenAIModel
import argparse
from prompt_library import few_shot_protoqa_prompt, few_shot_proofwriter_prompt
from prompt_library import few_shot_folio_prompt_fol, few_shot_logical_deduction_prompt
import random
import datetime

seed = 2024

# dongwei code
random.seed(seed)

class LogicProgramGenerator:
    def __init__(self, args):
        self.args = args
        self.data_path = args.data_path
        self.dataset_name = args.dataset_name
        self.split = args.split
        self.model_name = args.model_name
        self.save_path = args.save_path
        self.interpreter = args.interpreter

        self.openai_api = OpenAIModel(args.api_key, args.model_name, args.stop_words, args.max_new_tokens)
        self.prompt_creator = {'ProntoQA': self.prompt_prontoqa, 
                               'ProofWriter': self.prompt_proofwriter,
                               'FOLIO': self.prompt_folio,
                               'LogicalDeduction': self.prompt_logicaldeduction}
    
    def prompt_logicaldeduction(self, test_data):
        problem = test_data['context']
        question = test_data['question'].strip()
        options = '\n'.join(test_data['options']).strip()
        full_prompt = few_shot_logical_deduction_prompt % (problem, question, options)
        return full_prompt

    def prompt_prontoqa(self, test_data):
        problem = test_data['context']
        question = test_data['question'].replace('Is the following statement true or false?', '').strip()
        question = f'True or false: {question}'
        full_prompt = few_shot_protoqa_prompt % (problem, question)
        return full_prompt
    
    def prompt_proofwriter(self, test_data):
        problem = test_data['context']
        question = test_data['question'].strip()
        full_prompt = few_shot_proofwriter_prompt % (problem, question)
        return full_prompt
    
    def prompt_folio(self, test_data):
        problem = test_data['context']
        question = test_data['question'].strip()
        full_prompt = few_shot_folio_prompt_fol % (problem, question)
        return full_prompt

    def load_raw_dataset(self, split):
        with open(os.path.join(self.data_path, self.dataset_name, f'{split}.json')) as f:
            raw_dataset = json.load(f)
        return raw_dataset

    def logic_program_generation(self):
        # load raw dataset
        raw_dataset = self.load_raw_dataset(self.split)
        print(f"Loaded {len(raw_dataset)} examples from {self.split} split.")

        outputs = []
        for example in tqdm(raw_dataset):
            # create prompt
            try:
                full_prompt = self.prompt_creator[self.dataset_name](example)
                output = self.openai_api.generate(full_prompt)
                # print(full_prompt)
                programs = [output]

                # create output
                output = {'id': example['id'], 
                        'context': example['context'],
                        'question': example['question'], 
                        'answer': example['answer'],
                        'options': example['options'],
                        'raw_logic_programs': programs}
                outputs.append(output)
            except:
                print('Error in generating logic programs for example: ', example['id'])

        # save outputs        
        with open(os.path.join(self.save_path, self.interpreter, f'{self.dataset_name}_{self.split}_{self.model_name}.json'), 'w') as f:
            json.dump(outputs, f, indent=2, ensure_ascii=False)

    '''
    Updated version of logic_program_generation; speed up the generation process by batching
    '''
    def batch_logic_program_generation(self, batch_size = 1):
        # load raw dataset
        raw_dataset = self.load_raw_dataset(self.split)
        print(f"Loaded {len(raw_dataset)} examples from {self.split} split.")

        raw_dataset = random.sample(raw_dataset, 100)

        outputs = []
        # split dataset into chunks
        # dataset_chunks = [raw_dataset[i:i + batch_size] for i in range(0, len(raw_dataset), batch_size)]
        dataset_chunks = [raw_dataset[60: 100]]
        for chunk in tqdm(dataset_chunks):
            # create prompt
            full_prompts = [self.prompt_creator[self.dataset_name](example) for example in chunk]
            try:
                batch_outputs = self.openai_api.batch_generate(full_prompts)
                # create output
                for sample, output in zip(chunk, batch_outputs):
                    programs = [output]
                    output = {'id': sample['id'], 
                            'context': sample['context'],
                            'question': sample['question'], 
                            'answer': sample['answer'],
                            'options': sample['options'],
                            'raw_logic_programs': programs}
                    outputs.append(output)
            except:
                # generate one by one if batch generation fails
                for sample, full_prompt in zip(chunk, full_prompts):
                    try:
                        output = self.openai_api.generate(full_prompt)
                        programs = [output]
                        output = {'id': sample['id'], 
                                'context': sample['context'],
                                'question': sample['question'], 
                                'answer': sample['answer'],
                                'options': sample['options'],
                                'raw_logic_programs': programs}
                        outputs.append(output)
                    except:
                        print('Error in generating logic programs for example: ', sample['id'])

        # remove examples with duplicate ids from the result
        outputs = list({output['id']: output for output in outputs}.values())
        print(f"Generated {len(outputs)} examples.")
        
        # save outputs
        if not os.path.exists(os.path.join(self.save_path, self.interpreter)):
            os.makedirs(os.path.join(self.save_path, self.interpreter))
        timestamp = datetime.datetime.now().strftime('%Y_%b_%d_%H_%M_%S')
        with open(os.path.join(self.save_path, self.interpreter, f'{self.dataset_name}_{self.split}_{self.model_name}_{timestamp}.json'), 'w') as f:
            json.dump(outputs, f, indent=2, ensure_ascii=False)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, default='../data')
    parser.add_argument('--dataset_name', type=str)
    parser.add_argument('--split', type=str, default='dev')
    parser.add_argument('--save_path', type=str, default='./logic_programs')
    parser.add_argument('--interpreter', type=str)
    parser.add_argument('--api_key', type=str)
    parser.add_argument('--model_name', type=str, default='text-davinci-003')
    parser.add_argument('--stop_words', type=str, default='------')
    parser.add_argument('--max_new_tokens', type=int, default=1024)
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()
    logic_program_generator = LogicProgramGenerator(args)
    logic_program_generator.batch_logic_program_generation()