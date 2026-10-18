"""Exercise an independently running API, including repeated Hindi workers."""
import json
import time
import urllib.request
import urllib.error


def main():
    base='http://127.0.0.1:8000'
    for attempt in range(30):
        try:
            with urllib.request.urlopen(base+'/api/health',timeout=5) as response:
                assert json.load(response)['status']=='ready'
            break
        except (OSError, AssertionError):
            if attempt==29: raise
            time.sleep(2)
    for payload in [
        {'description':'someone who loves collecting books','language':'en'},
        {'description':'किताबों से प्रेम करने वाला व्यक्ति','language':'en'},
        {'description':'a person who writes poems','language':'hi'},
        {'description':'किताबों से प्रेम करने वाला व्यक्ति','language':'both'},
        {'description':'someone who loves books','language':'en','starting_letter':'bib'},
    ]:
        request=urllib.request.Request(base+'/api/predict',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=60) as response:
            result=json.load(response)
        assert result['suggestions'],result
        if payload.get('starting_letter'):
            assert all(s['word'].lower().startswith('bib') for s in result['suggestions'])
        print(payload['language'],result['elapsed_ms'],flush=True)
    print('Deployment smoke checks passed.',flush=True)


if __name__=='__main__': main()
