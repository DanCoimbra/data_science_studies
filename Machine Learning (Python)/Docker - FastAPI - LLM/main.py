import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_src = "microsoft/DialoGPT-large"
model     = AutoModelForCausalLM.from_pretrained(model_src)
tokenizer = AutoTokenizer.from_pretrained(model_src)

n_steps = 5
chat_enc = torch.tensor([]).long().to(model.device)
first_prompt = "What is the capital of Uzbekistan?"
for step in range(n_steps):
    prompt = first_prompt if step == 0 else input(">> User: ") + tokenizer.eos_token
    if step == 0:
        print(f">> User: {prompt}")
    prompt_enc = tokenizer.encode(prompt, return_tensors='pt').to(model.device)
    prompt_enc = torch.cat([chat_enc, prompt_enc], dim=-1)

    pad_token_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    att_msk = (prompt_enc != tokenizer.pad_token_id).long()
    chat_enc = model.generate(prompt_enc, max_length=1000, pad_token_id=tokenizer.eos_token_id, attention_mask=att_msk)
    
    answer_enc = chat_enc[:, prompt_enc.shape[-1]:][0]
    answer = tokenizer.decode(answer_enc, skip_special_tokens=True)

    print(f"Pad token ID: {pad_token_id}")
    print(f"Tokenizer pad token ID: {tokenizer.pad_token_id}")
    print(f"EOS token ID: {tokenizer.eos_token_id}")
    print(f"EOS token: {tokenizer.eos_token}")
    print(f"Answer ID: {answer_enc}")
    print(f"{model_src}: {answer}")