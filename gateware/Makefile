
build/top.fs: build.py audio_selector.py io_defs.py gpio.py
	./build.py --dot test.png --prog

i9: build.py audio_selector.py io_defs.py gpio.py
	./build.py --dot test.png --prog --platform=i9

soc: build.py audio_selector.py io_defs.py gpio.py
	./tang_nano_soc.py --csr-csv csr.csv --soc-json=soc.json --build --flash

clean:
	rm -rf build
	find . -name "*~" | xargs rm

ctags:
	ctags -R .

#	FIN
