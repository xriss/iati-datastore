import os
import codecs
import logging
import datetime as dt

import requests
from flask.ext.script import Manager
from sqlalchemy import not_

from iatilib.frontend import create_app
from iatilib import parse, codelists, model, db, redis
from iatilib.crawler import manager as crawler_manager
from iatilib.queue import manager as queue_manager


manager = Manager(create_app(DEBUG=True))
manager.add_command("crawl", crawler_manager)
manager.add_command("queue", queue_manager)


@manager.shell
def make_shell_context():
    return dict(
        app=manager.app,
        db=db,
        rdb=redis,
        model=model,
        codelists=codelists)


@manager.command
def download_codelists():
    "Download CSV codelists from IATI"
    for name, url in codelists.urls.items():
        filename = "iati_datastore/iatilib/codelists/%s.csv" % name
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            print filename, "exists, skipping"
        else:
            print "Downloading", name
            resp = requests.get(url)
            resp.raise_for_status()
            assert len(resp.text) > 0, "Response is empty"
            with codecs.open(filename, "w", encoding="utf-8") as cl:
                cl.write(resp.text)


@manager.command
def cleanup():
    from iatilib.model import Log
    db.session.query(Log).filter(
        Log.created_at < dt.datetime.utcnow() - dt.timedelta(days=5)
    ).filter(not_(Log.logger.in_(
        ['activity_importer', 'failed_activity', 'xml_parser']),
    )).delete('fetch')
    db.session.commit()
    db.engine.dispose()
    

@manager.option(
    '-x', '--fail-on-xml-errors',
    action="store_true", dest="fail_xml")
@manager.option(
    '-s', '--fail-on-spec-errors',
    action="store_true", dest="fail_spec")
@manager.option('-v', '--verbose', action="store_true")
@manager.option('filenames', nargs='+')
def parse_file(filenames, verbose=False, fail_xml=False, fail_spec=False):
    for filename in filenames:
        if verbose:
            print "Parsing", filename
        try:
            db.session.add_all(parse.document(filename))
            db.session.commit()
        except parse.ParserError, exc:
            logging.error("Could not parse file %r", filename)
            db.session.rollback()
            if isinstance(exc, parse.XMLError) and fail_xml:
                raise
            if isinstance(exc, parse.SpecError) and fail_spec:
                raise


@manager.command
def create_database():
    db.create_all()

#
# possible exchange rates, euro based, so 1999 onwards only?
#
# http://www.ecb.europa.eu/stats/exchange/eurofxref/html/index.en.html
# http://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip
#

from StringIO import StringIO
from zipfile import ZipFile
from datetime import datetime
import csv,math

fx_url= "http://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"
fx_name="iati_datastore/iatilib/cache/eurofxref-hist.csv"


@manager.command
def download_fx():
	"donwload currency exchange csv"
	print "Downloading", fx_url
	r = requests.get(fx_url)
	r.raise_for_status()
	assert len(r.content) > 0, "Response is empty"
	zf=ZipFile(StringIO(r.content))
	fp=zf.open("eurofxref-hist.csv")

	with codecs.open(fx_name, "w", encoding="utf-8") as cl:
		for line in fp.readlines():
			cl.write(line)

	print "Saved", fx_name


def tonumber(s):
	try:
		return float(s)
	except ValueError:
		return False

def tomember(v,s):
	try:
		return v[s]
	except KeyError:
		return False

@manager.command
def import_fx():
	"import currency exchange csv"
	print "Loading", fx_name

	with open(fx_name, 'rb') as csvfile:
		reader = csv.reader(csvfile)
		headers=reader.next()
		rows={}
		print ', '.join(headers)	#headers
		i=0
		for row in reader:
			i+=1
			d=datetime.strptime(row[0], "%Y-%m-%d")
			um= ((d.year-1970)*12) + (d.month-1) # months since 1970
			rows[um]=tomember(rows,um) or {}
			r=rows[um]
			for i,v in enumerate(headers) :
				if i>0:
					n=tonumber(row[i]) or 0
					r[i]=(tomember(r,i) or 0)+n
			r[0]=( tomember(r,0) or 0 )+1	# keep count in [0]
#			print(um,r[0])

		kmin=min(rows)					# calculate the range of values we have
		kmax=max(rows)
		print("minmax",kmin,kmax)

		for m in range(kmin,kmax+1) :	#range is off by one...
			r=rows[m]
			for i,v in enumerate(headers) :
				if i>0:
					r[i]=(r[i]/r[0])	# just average all values we have for each month
			r[0]=m						# count now becomes the month index

		for m in range(kmin,kmax+1) :
			r=rows[m]
			for i,v in enumerate(headers) :
				if i>0:
					if rows[m][i]==0 :	# need to fill with a value from closest other month with actual value
						n=0
						while ( m+n <= kmax ) or ( m-n >= kmin ) : # while in range? we should have some values
							r=tomember(rows,m+n)
							if r and r[i]!=0 :		# found value?
								rows[m][i]=r[i]
								break
							r=tomember(rows,m-n)
							if r and r[i]!=0 :		# found value?
								rows[m][i]=r[i]
								break
							n+=1

#now have, reasonable values for every month in the range we know about, stuffit into the database for later use
		for m in range(kmin,kmax+1) :
			r=rows[m]
#			print(r)
			
			
			
def main():
    manager.run()

if __name__ == "__main__":
    main()

