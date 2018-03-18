all:
	platex -halt-on-error -shell-escape tuna_manual.tex
	dvipdfmx tuna_manual.dvi

clean:
	rm -rf *.aux *.dvi *.log *.pdf *.pyg *.toc _minted*
