import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_src = "microsoft/DialoGPT-small"
model     = AutoModelForCausalLM.from_pretrained(model_src)
tokenizer = AutoTokenizer.from_pretrained(model_src)

n_steps = 5
chat_enc = torch.tensor([]).long().to(model.device)

for step in range(n_steps):
    prompt = input(">> User:") + tokenizer.eos_token
    prompt_enc = tokenizer.encode(prompt, return_tensors='pt').to(model.device)
    chat_enc = torch.cat([chat_enc, prompt_enc], dim=-1)

    pad_token_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    att_msk = (chat_enc != pad_token_id).long()
    answer_enc = model.generate(chat_enc, max_length=1000, pad_token_id=tokenizer.eos_token_id, attention_mask=att_msk)
    chat_enc = torch.cat([chat_enc, answer_enc], dim=-1)
    
    answer = tokenizer.decode(answer_enc[0], skip_special_tokens=True)
    print(f"DialoGPT-small: {answer}")
    
