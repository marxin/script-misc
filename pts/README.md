Benchmarks are listed with:
```
phoronix-test-suite list-tests | grep 'pts/' | grep Processor | cut -f1 -d' '
```

Then I build benchmarks with:
```
phoronix-test-suite batch-install `cat tests.txt | grep -v '#' | tr -s '\n' ' '`
```
