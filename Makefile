JADE = $(shell find jade/*.jade ! -name 'layout.jade')
HTML = $(patsubst jade/%.jade, pages/%.html, $(JADE))

all: $(HTML)

pages/%.html: jade/%.jade
	jade < $< --out $< --path $< --pretty > $@

clean:
	rm -f $(HTML)

.PHONY: clean
