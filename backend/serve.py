import os
from .config import DATA


if __name__=='__main__':
    if not (DATA/'compact'/'metadata.json').exists():
        from .bootstrap import main
        main()
    import uvicorn
    uvicorn.run('backend.main:app',host='0.0.0.0',port=int(os.environ.get('PORT','8000')),workers=1)
