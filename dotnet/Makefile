
all: blobct.dll testapp.exe

blobct.dll: blobct.cs
	gmcs -debug+ -warnaserror -out:$@ -target:library $<

foo_gen.cs: foo.blob
	python ../blobc.py -l csharp -o $@ $<

testgen.dll: foo_gen.cs blobct.dll
	gmcs -debug+ -warnaserror -out:$@ -r:blobct.dll -target:library foo_gen.cs

testapp.exe: test.cs testgen.dll
	gmcs -debug+ -warnaserror -out:$@ -r:testgen.dll -r:blobct.dll -target:exe test.cs

clean:
	rm -f blobct.dll testgen.dll testapp.exe foo_gen.cs *.mdb
