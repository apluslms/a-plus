# Creating tests

1. Run A+ locally using the [develop-aplus](https://github.com/apluslms/develop-aplus) repository
```
source .venv/bin/activate
./docker-up.sh
```

2. Begin "recording" a test in the browser
```
playwright codegen --target python-pytest localhost:8000
```

3. Copy the generated test code to a Python file

## Documentation

[Generating tests](https://playwright.dev/python/docs/codegen-intro)

[Writing tests](https://playwright.dev/python/docs/writing-tests)

[Running and debugging tests](https://playwright.dev/python/docs/running-tests)

[Trace viewer](https://playwright.dev/python/docs/trace-viewer-intro)
