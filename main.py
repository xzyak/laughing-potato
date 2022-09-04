import json
import random
from collections import OrderedDict
from uuid import uuid4
from fastapi import Body, FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()


class Toss(BaseModel):
    toss_id: str
    amount: int


@app.post('/bank/create', name='요청 생성',
          description='요청 시 해당 요청의 UUID를 제공합니다.<br>설정에서 전체-내 토스아이디-돈 받은 내역을 켜두셔야 합니다.')
async def bank_start(toss: Toss):
    html_req = requests.get(f'https://toss.me/{toss.toss_id}')
    ref_id = html_req.text.split('{\\"refId\\":')[1].split(',\\"word\\"')[0]
    print(ref_id)

    current_uuid, name = uuid4(), str(random.randint(500, 1000))
    cash_req = requests.post(
        f"https://api-gateway.toss.im:11099/api-public/v3/cashtag/transfer-feed/received/list?inputWord={toss.toss_id}",
        headers={"X-Toss-Method": "GET"}
    )
    cash_data = cash_req.json()

    profile_req = requests.get(
        f"https://api-gateway.toss.im:11099/api-public/v3/cashtag/profile/get-transfer-info?refId={ref_id}&webSessionKey={current_uuid}"
    )
    profile_data = profile_req.json()

    if cash_data['resultType'] == "SUCCESS":
        cash_data = cash_data['success']['data']
        file_data = OrderedDict()
        file_data['toss_id'], file_data['name'], file_data['price'], file_data['data'] = toss.toss_id, name, toss.amount, cash_data
        with open(f'{current_uuid}.json', 'w', encoding='utf-8') as f:
            json.dump(file_data, f, ensure_ascii=False, indent='\t')

        return {"result": True, "message": "success", "uuid": current_uuid, "name": name,
                "bankacc": profile_data['success']['virtualAccountNumber']}

    return {"result": False, "message": cash_data['error']['reason']}


@app.post('/bank/confirm', name='결제요청 확인',
          description='요청 생성 시 왔던 UUID를 사용하여 결제 요청을 확인합니다.<br>모든 테스크가 끝나면 자동으로 파일을 삭제합니다.')
async def bank_start(uuid: str = Body()):
    with open(f'{uuid}.json', 'r', encoding='utf-8') as f:
        file_data = json.load(f)

    cash_req = requests.post(
        f"https://api-gateway.toss.im:11099/api-public/v3/cashtag/transfer-feed/received/list?inputWord={file_data['toss_id']}",
        headers={"X-Toss-Method": "GET"}
    )
    cash_data = cash_req.json()['success']['data']
    censored_name_list = list(file_data['name'])
    censored_name_list[1] = '*'
    censored_name = "".join(censored_name_list)

    if not cash_data == file_data:
        for data in cash_data:
            if data['senderDisplayName'] == censored_name and data['amount'] == file_data['amount']:
                return {"result": True, "amount": data['amount']}
        return {"result": False, "message": "아직 송금되지 않았습니다."}
    else:
        return {"result": False, "message": "요청 이후 송금된 기록이 없습니다."}
