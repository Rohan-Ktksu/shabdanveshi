"""Exercise a running API, including cache hits, model switches and strict clues."""
import json
import os
import time
import urllib.request
import urllib.error


def main():
    base=os.environ.get('SHABD_SMOKE_URL', 'http://127.0.0.1:8000').rstrip('/')
    for attempt in range(90):
        try:
            with urllib.request.urlopen(base+'/api/health',timeout=5) as response:
                assert json.load(response)['status']=='ready'
            break
        except (OSError, AssertionError):
            if attempt==89: raise
            time.sleep(2)
    for payload in [
        {'description':'someone who loves collecting books','language':'en'},
        {'description':'a feeling of longing for the past','language':'en'},
        {'description':'someone who loves collecting books','language':'en'},
        {'description':'किताबों से प्रेम करने वाला व्यक्ति','language':'en'},
        {'description':'a person who writes poems','language':'hi'},
        {'description':'किताबों से प्रेम करने वाला व्यक्ति','language':'both'},
        {'description':'समय को मापने वाला उपकरण','language':'en'},
        {'description':'someone who loves books','language':'en','starting_letter':'bib'},
        {'description':'someone who loves books','language':'en','starting_letter':'zzzzzzzz'},
    ]:
        request=urllib.request.Request(base+'/api/predict',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=180) as response:
            result=json.load(response)
        if payload.get('starting_letter') == 'zzzzzzzz':
            assert result['suggestions'] == [], result
            continue
        assert result['suggestions'],result
        if payload['language'] != 'both':
            assert all(s['language'] == payload['language'] for s in result['suggestions']), result
        if payload['description'] == 'someone who loves collecting books':
            assert result['suggestions'][0]['word'] == 'bibliophile', result
        if payload['description'] == 'किताबों से प्रेम करने वाला व्यक्ति':
            assert result['translated_query'], result
        if payload.get('starting_letter'):
            assert all(s['word'].lower().startswith('bib') for s in result['suggestions'])
        print(payload['language'],result['elapsed_ms'],flush=True)
    print('Deployment smoke checks passed.',flush=True)


if __name__=='__main__': main()
