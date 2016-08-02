# -*- coding: utf-8 -*-
"""
The Supreme Court Corpus
------------------------

Download to and stream from disk a corpus of all decisions issued by the U.S.
Supreme Court from 1792 through 2016. That amounts to 23k documents and 120.5M
tokens. Each document contains 5 fields:

    * text: full text of the Court's decision
    * title: title of the court case, in all caps
    * docket: docket number of the court case, which some may find useful
    * decided_date: date on which the decision was given, as an ISO-standard string
    * argued_date: date on which the case was argued before the Supreme Court,
        as an ISO-standard string (NOTE: about half are missing this value)

This dataset was derived from `FindLaw's searchable database <http://caselaw.findlaw.com/court/us-supreme-court>`_
of court cases. Its creation was inspired by `this blog post <http://www.emilyinamillion.me/blog/2016/7/13/visualizing-supreme-court-topics-over-time>`_
by Emily Barry.
"""
import io
import logging
import os

import requests

from textacy import __resources_dir__
from textacy.compat import PY2, string_types
from textacy.fileio import make_dirs, read_json_lines

if PY2:
    URL = 'https://s3.amazonaws.com/chartbeat-labs/supreme-court-cases-py2.json.gz'
else:
    URL = 'https://s3.amazonaws.com/chartbeat-labs/supreme-court-cases-py3.json.gz'
FILENAME = URL.rsplit('/', 1)[-1]

MIN_DATE = '1792-08-01'
MAX_DATE = '2016-07-18'

LOGGER = logging.getLogger(__name__)

# TODO: Consider joining data with http://supremecourtdatabase.org/index.php


class SupremeCourt(object):

    decision_author_codes = {
        1: 'Jay, John',
        2: 'Rutledge, John',
        3: 'Cushing, William',
        4: 'Wilson, James',
        5: 'Blair,  John',
        6: 'Iredell, James',
        7: 'Johnson, Thomas',
        8: 'Paterson, William',
        9: 'Rutledge, John',
        10: 'Chase, Samuel',
        11: 'Ellsworth, Oliver',
        12: 'Washington, Bushrod',
        13: 'Moore, Alfred',
        14: 'Marshall, John',
        15: 'Johnson, William',
        16: 'Livingston, Henry',
        17: 'Todd, Thomas',
        18: 'Duvall, Gabriel',
        19: 'Story, Joseph',
        20: 'Thompson, Smith',
        21: 'Trimble, Robert',
        22: 'McLean, John',
        23: 'Baldwin, Henry',
        24: 'Wayne, James',
        25: 'Taney, Roger',
        26: 'Barbour, Philip',
        27: 'Catron, John',
        28: 'McKinley, John',
        29: 'Daniel, Peter',
        30: 'Nelson, Samuel',
        31: 'Woodbury, Levi',
        32: 'Grier, Robert',
        33: 'Curtis, Benjamin',
        34: 'Campbell, John',
        35: 'Clifford, Nathan',
        36: 'Swayne, Noah',
        37: 'Miller, Samuel',
        38: 'Davis, David',
        39: 'Field, Stephen',
        40: 'Chase, Salmon',
        41: 'Strong, William',
        42: 'Bradley, Joseph',
        43: 'Hunt, Ward',
        44: 'Waite, Morrison',
        45: 'Harlan, John',
        46: 'Woods, William',
        47: 'Matthews, Stanley',
        48: 'Gray, Horace',
        49: 'Blatchford, Samuel',
        50: 'Lamar, Lucius',
        51: 'Fuller, Melville',
        52: 'Brewer, David',
        53: 'Brown, Henry',
        54: 'Shiras,  George',
        55: 'Jackson, Howell',
        56: 'White, Edward',
        57: 'Peckham, Rufus',
        58: 'McKenna, Joseph',
        59: 'Holmes, Oliver',
        60: 'Day, William',
        61: 'Moody, William',
        62: 'Lurton, Horace',
        63: 'Hughes, Charles',
        64: 'Van Devanter, Willis',
        65: 'Lamar, Joseph',
        66: 'Pitney, Mahlon',
        67: 'McReynolds, James',
        68: 'Brandeis, Louis',
        69: 'Clarke, John',
        70: 'Taft, William',
        71: 'Sutherland, George',
        72: 'Butler, Pierce',
        73: 'Sanford, Edward',
        74: 'Stone, Harlan',
        75: 'Hughes, Charles',
        76: 'Roberts, Owen',
        77: 'Cardozo, Benjamin',
        78: 'Black, Hugo',
        79: 'Reed, Stanley',
        80: 'Frankfurter, Felix',
        81: 'Douglas, William',
        82: 'Murphy, Francis',
        83: 'Byrnes, James',
        84: 'Jackson, Robert',
        85: 'Rutledge, Wiley',
        86: 'Burton, Harold',
        87: 'Vinson, Fred',
        88: 'Clark, Tom',
        89: 'Minton, Sherman',
        90: 'Warren, Earl',
        91: 'Harlan, John',
        92: 'Brennan, William',
        93: 'Whittaker, Charles',
        94: 'Stewart, Potter',
        95: 'White, Byron',
        96: 'Goldberg, Arthur',
        97: 'Fortas, Abe',
        98: 'Marshall, Thurgood',
        99: 'Burger, Warren',
        100: 'Blackmun, Harry',
        101: 'Powell, Lewis',
        102: 'Rehnquist, William',
        103: 'Stevens, John',
        104: "O'Connor, Sandra",
        105: 'Scalia, Antonin',
        106: 'Kennedy, Anthony',
        107: 'Souter, David',
        108: 'Thomas, Clarence',
        109: 'Ginsburg, Ruth',
        110: 'Breyer, Stephen',
        111: 'Roberts, John',
        112: 'Alito, Samuel',
        113: 'Sotomayor, Sonia',
        114: 'Kagan, Elena'}

    issue_area_codes = {
        1: 'Criminal Procedure',
        2: 'Civil Rights',
        3: 'First Amendment',
        4: 'Due Process',
        5: 'Privacy',
        6: 'Attorneys',
        7: 'Unions',
        8: 'Economic Activity',
        9: 'Judicial Power',
        10: 'Federalism',
        11: 'Interstate Relations',
        12: 'Federal Taxation',
        13: 'Miscellaneous',
        14: 'Private Action'}

    issue_codes = {
        '100010': 'federal-state ownership dispute (cf. Submerged Lands Act)',
        '100020': 'federal pre-emption of state court jurisdiction',
        '100030': 'federal pre-emption of state legislation or regulation. cf. state regulation of business. rarely involves union activity. Does not involve constitutional interpretation unless the Court says it does.',
        '100040': 'Submerged Lands Act (cf. federal-state ownership dispute)',
        '100050': 'national supremacy: commodities',
        '100060': 'national supremacy: intergovernmental tax immunity',
        '100070': 'national supremacy: marital and family relationships and property, including obligation of child support',
        '100080': 'national supremacy: natural resources (cf. natural resources - environmental protection)',
        '100090': 'national supremacy: pollution, air or water (cf. natural resources - environmental protection)',
        '10010': 'involuntary confession',
        '100100': 'national supremacy: public utilities (cf. federal public utilities regulation)',
        '100110': 'national supremacy: state tax (cf. state tax)',
        '100120': 'national supremacy: miscellaneous',
        '100130': 'miscellaneous federalism',
        '10020': 'habeas corpus',
        '10030': 'plea bargaining: the constitutionality of and/or the circumstances of its exercise',
        '10040': 'retroactivity (of newly announced or newly enacted constitutional or statutory rights)',
        '10050': 'search and seizure (other than as pertains to vehicles or Crime Control Act)',
        '10060': 'search and seizure, vehicles',
        '10070': 'search and seizure, Crime Control Act',
        '10080': 'contempt of court or congress',
        '10090': 'self-incrimination (other than as pertains to Miranda or immunity from prosecution)',
        '10100': 'Miranda warnings',
        '10110': 'self-incrimination, immunity from prosecution',
        '10120': 'right to counsel (cf. indigents appointment of counsel or inadequate representation)',
        '10130': 'cruel and unusual punishment, death penalty (cf. extra legal jury influence, death penalty)',
        '10140': 'cruel and unusual punishment, non-death penalty (cf. liability, civil rights acts)',
        '10150': 'line-up',
        '10160': 'discovery and inspection (in the context of criminal litigation only, otherwise Freedom of Information Act and related federal or state statutes or regulations)',
        '10170': 'double jeopardy',
        '10180': 'ex post facto (state)',
        '10190': 'extra-legal jury influences: miscellaneous',
        '10200': 'extra-legal jury influences: prejudicial statements or evidence',
        '10210': 'extra-legal jury influences: contact with jurors outside courtroom',
        '10220': 'extra-legal jury influences: jury instructions (not necessarily in criminal cases)',
        '10230': 'extra-legal jury influences: voir dire (not necessarily a criminal case)',
        '10240': 'extra-legal jury influences: prison garb or appearance',
        '10250': 'extra-legal jury influences: jurors and death penalty (cf. cruel and unusual punishment)',
        '10260': 'extra-legal jury influences: pretrial publicity',
        '10270': 'confrontation (right to confront accuser, call and cross-examine witnesses)',
        '10280': 'subconstitutional fair procedure: confession of error',
        '10290': 'subconstitutional fair procedure: conspiracy (cf. Federal Rules of Criminal Procedure: conspiracy)',
        '10300': 'subconstitutional fair procedure: entrapment',
        '10310': 'subconstitutional fair procedure: exhaustion of remedies',
        '10320': 'subconstitutional fair procedure: fugitive from justice',
        '10330': 'subconstitutional fair procedure: presentation, admissibility, or sufficiency of evidence (not necessarily a criminal case)',
        '10340': 'subconstitutional fair procedure: stay of execution',
        '10350': 'subconstitutional fair procedure: timeliness',
        '10360': 'subconstitutional fair procedure: miscellaneous',
        '10370': 'Federal Rules of Criminal Procedure',
        '10380': 'statutory construction of criminal laws: assault',
        '10390': 'statutory construction of criminal laws: bank robbery',
        '10400': 'statutory construction of criminal laws: conspiracy (cf. subconstitutional fair procedure: conspiracy)',
        '10410': 'statutory construction of criminal laws: escape from custody',
        '10420': 'statutory construction of criminal laws: false statements (cf. statutory construction of criminal laws: perjury)',
        '10430': 'statutory construction of criminal laws: financial (other than in fraud or internal revenue)',
        '10440': 'statutory construction of criminal laws: firearms',
        '10450': 'statutory construction of criminal laws: fraud',
        '10460': 'statutory construction of criminal laws: gambling',
        '10470': 'statutory construction of criminal laws: Hobbs Act; i.e., 18 USC 1951',
        '10480': 'statutory construction of criminal laws: immigration (cf. immigration and naturalization)',
        '10490': 'statutory construction of criminal laws: internal revenue (cf. Federal Taxation)',
        '10500': 'statutory construction of criminal laws: Mann Act and related statutes',
        '10510': 'statutory construction of criminal laws: narcotics includes regulation and prohibition of alcohol',
        '10520': 'statutory construction of criminal laws: obstruction of justice',
        '10530': 'statutory construction of criminal laws: perjury (other than as pertains to statutory construction of criminal laws: false statements)',
        '10540': 'statutory construction of criminal laws: Travel Act, 18 USC 1952',
        '10550': 'statutory construction of criminal laws: war crimes',
        '10560': 'statutory construction of criminal laws: sentencing guidelines',
        '10570': 'statutory construction of criminal laws: miscellaneous',
        '10580': 'jury trial (right to, as distinct from extra-legal jury influences)',
        '10590': 'speedy trial',
        '10600': "miscellaneous criminal procedure (cf. due process, prisoners' rights, comity: criminal procedure)",
        '110010': 'boundary dispute between states',
        '110020': 'non-real property dispute between states',
        '110030': 'miscellaneous interstate relations conflict',
        '110033': 'incorporation of foreign territories',
        '120010': 'federal taxation, typically under provisions of the Internal Revenue Code',
        '120020': 'federal taxation of gifts, personal, business, or professional expenses',
        '120030': 'priority of federal fiscal claims: over those of the states or private entities',
        '120040': 'miscellaneous federal taxation (cf. national supremacy: state tax)',
        '130010': 'legislative veto',
        '130015': 'executive authority vis-a-vis congress or the states',
        '130020': 'miscellaneous',
        '140010': 'real property',
        '140020': 'personal property',
        '140030': 'contracts',
        '140040': 'evidence',
        '140050': 'civil procedure',
        '140060': 'torts',
        '140070': 'wills and trusts',
        '140080': 'commercial transactions',
        '20010': 'voting',
        '20020': 'Voting Rights Act of 1965, plus amendments',
        '20030': 'ballot access (of candidates and political parties)',
        '20040': 'desegregation (other than as pertains to school desegregation, employment discrimination, and affirmative action)',
        '20050': 'desegregation, schools',
        '20060': 'employment discrimination: on basis of race, age, religion, illegitimacy, national origin, or working conditions.',
        '20070': 'affirmative action',
        '20075': 'slavery or indenture',
        '20080': 'sit-in demonstrations (protests against racial discrimination in places of public accommodation)',
        '20090': 'reapportionment: other than plans governed by the Voting Rights Act',
        '20100': "debtors' rights",
        '20110': 'deportation (cf. immigration and naturalization)',
        '20120': 'employability of aliens (cf. immigration and naturalization)',
        '20130': 'sex discrimination (excluding sex discrimination in employment)',
        '20140': 'sex discrimination in employment (cf. sex discrimination)',
        '20150': 'Indians (other than pertains to state jurisdiction over)',
        '20160': 'Indians, state jurisdiction over',
        '20170': 'juveniles (cf. rights of illegitimates)',
        '20180': 'poverty law, constitutional',
        '20190': 'poverty law, statutory: welfare benefits, typically under some Social Security Act provision.',
        '20200': "illegitimates, rights of (cf. juveniles): typically inheritance and survivor's benefits, and paternity suits",
        '20210': 'handicapped, rights of: under Rehabilitation, Americans with Disabilities Act, and related statutes',
        '20220': 'residency requirements: durational, plus discrimination against nonresidents',
        '20230': 'military: draftee, or person subject to induction',
        '20240': 'military: active duty',
        '20250': 'military: veteran',
        '20260': 'immigration and naturalization: permanent residence',
        '20270': 'immigration and naturalization: citizenship',
        '20280': 'immigration and naturalization: loss of citizenship, denaturalization',
        '20290': 'immigration and naturalization: access to public education',
        '20300': 'immigration and naturalization: welfare benefits',
        '20310': 'immigration and naturalization: miscellaneous',
        '20320': 'indigents: appointment of counsel (cf. right to counsel)',
        '20330': 'indigents: inadequate representation by counsel (cf. right to counsel)',
        '20340': 'indigents: payment of fine',
        '20350': 'indigents: costs or filing fees',
        '20360': 'indigents: U.S. Supreme Court docketing fee',
        '20370': 'indigents: transcript',
        '20380': 'indigents: assistance of psychiatrist',
        '20390': 'indigents: miscellaneous',
        '20400': 'liability, civil rights acts (cf. liability, governmental and liability, nongovernmental; cruel and unusual punishment, non-death penalty)',
        '20410': 'miscellaneous civil rights (cf. comity: civil rights)',
        '30010': 'First Amendment, miscellaneous (cf. comity: First Amendment)',
        '30020': 'commercial speech, excluding attorneys',
        '30030': 'libel, defamation: defamation of public officials and public and private persons',
        '30040': 'libel, privacy: true and false light invasions of privacy',
        '30050': 'legislative investigations: concerning internal security only',
        '30060': 'federal or state internal security legislation: Smith, Internal Security, and related federal statutes',
        '30070': 'loyalty oath or non-Communist affidavit (other than bar applicants, government employees, political party, or teacher)',
        '30080': 'loyalty oath: bar applicants (cf. admission to bar, state or federal or U.S. Supreme Court)',
        '30090': 'loyalty oath: government employees',
        '30100': 'loyalty oath: political party',
        '30110': 'loyalty oath: teachers',
        '30120': 'security risks: denial of benefits or dismissal of employees for reasons other than failure to meet loyalty oath requirements',
        '30130': 'conscientious objectors (cf. military draftee or military active duty) to military service',
        '30140': 'campaign spending (cf. governmental corruption):',
        '30150': 'protest demonstrations (other than as pertains to sit-in demonstrations): demonstrations and other forms of protest based on First Amendment guarantees',
        '30160': 'free exercise of religion',
        '30170': 'establishment of religion (other than as pertains to parochiaid:)',
        '30180': 'parochiaid: government aid to religious schools, or religious requirements in public schools',
        '30190': 'obscenity, state (cf. comity: privacy): including the regulation of sexually explicit material under the 21st Amendment',
        '30200': 'obscenity, federal',
        '40010': 'due process: miscellaneous (cf. loyalty oath), the residual code',
        '40020': "due process: hearing or notice (other than as pertains to government employees or prisoners' rights)",
        '40030': 'due process: hearing, government employees',
        '40040': "due process: prisoners' rights and defendants' rights",
        '40050': 'due process: impartial decision maker',
        '40060': 'due process: jurisdiction (jurisdiction over non-resident litigants)',
        '40070': 'due process: takings clause, or other non-constitutional governmental taking of property',
        '50010': 'privacy (cf. libel, comity: privacy)',
        '50020': 'abortion: including contraceptives',
        '50030': 'right to die',
        '50040': 'Freedom of Information Act and related federal or state statutes or regulations',
        '60010': "attorneys' and governmental employees' or officials' fees or compensation or licenses",
        '60020': 'commercial speech, attorneys (cf. commercial speech)',
        '60030': 'admission to a state or federal bar, disbarment, and attorney discipline (cf. loyalty oath: bar applicants)',
        '60040': 'admission to, or disbarment from, Bar of the U.S. Supreme Court',
        '70010': 'arbitration (in the context of labor-management or employer-employee relations) (cf. arbitration)',
        '70020': 'union antitrust: legality of anticompetitive union activity',
        '70030': 'union or closed shop: includes agency shop litigation',
        '70040': 'Fair Labor Standards Act',
        '70050': 'Occupational Safety and Health Act',
        '70060': 'union-union member dispute (except as pertains to union or closed shop)',
        '70070': 'labor-management disputes: bargaining',
        '70080': 'labor-management disputes: employee discharge',
        '70090': 'labor-management disputes: distribution of union literature',
        '70100': 'labor-management disputes: representative election',
        '70110': 'labor-management disputes: antistrike injunction',
        '70120': 'labor-management disputes: jurisdictional dispute',
        '70130': 'labor-management disputes: right to organize',
        '70140': 'labor-management disputes: picketing',
        '70150': 'labor-management disputes: secondary activity',
        '70160': 'labor-management disputes: no-strike clause',
        '70170': 'labor-management disputes: union representatives',
        '70180': 'labor-management disputes: union trust funds (cf. ERISA)',
        '70190': 'labor-management disputes: working conditions',
        '70200': 'labor-management disputes: miscellaneous dispute',
        '70210': 'miscellaneous union',
        '80010': 'antitrust (except in the context of mergers and union antitrust)',
        '80020': 'mergers',
        '80030': 'bankruptcy (except in the context of priority of federal fiscal claims)',
        '80040': "sufficiency of evidence: typically in the context of a jury's determination of compensation for injury or death",
        '80050': 'election of remedies: legal remedies available to injured persons or things',
        '80060': 'liability, governmental: tort or contract actions by or against government or governmental officials other than defense of criminal actions brought under a civil rights action.',
        '80070': 'liability, other than as in sufficiency of evidence, election of remedies, punitive damages',
        '80080': 'liability, punitive damages',
        '80090': 'Employee Retirement Income Security Act (cf. union trust funds)',
        '80100': 'state or local government tax',
        '80105': 'state and territorial land claims',
        '80110': 'state or local government regulation, especially of business (cf. federal pre-emption of state court jurisdiction, federal pre-emption of state legislation or regulation)',
        '80120': 'federal or state regulation of securities',
        '80130': 'natural resources - environmental protection (cf. national supremacy: natural resources, national supremacy: pollution)',
        '80140': 'corruption, governmental or governmental regulation of other than as in campaign spending',
        '80150': "zoning: constitutionality of such ordinances, or restrictions on owners' or lessors' use of real property",
        '80160': 'arbitration (other than as pertains to labor-management or employer-employee relations (cf. union arbitration)',
        '80170': 'federal or state consumer protection: typically under the Truth in Lending; Food, Drug and Cosmetic; and Consumer Protection Credit Acts',
        '80180': 'patents and copyrights: patent',
        '80190': 'patents and copyrights: copyright',
        '80200': 'patents and copyrights: trademark',
        '80210': 'patents and copyrights: patentability of computer processes',
        '80220': 'federal or state regulation of transportation regulation: railroad',
        '80230': 'federal and some few state regulations of transportation regulation: boat',
        '80240': 'federal and some few state regulation of transportation regulation:truck, or motor carrier',
        '80250': 'federal and some few state regulation of transportation regulation: pipeline (cf. federal public utilities regulation: gas pipeline)',
        '80260': 'federal and some few state regulation of transportation regulation: airline',
        '80270': 'federal and some few state regulation of public utilities regulation: electric power',
        '80280': 'federal and some few state regulation of public utilities regulation: nuclear power',
        '80290': 'federal and some few state regulation of public utilities regulation: oil producer',
        '80300': 'federal and some few state regulation of public utilities regulation: gas producer',
        '80310': 'federal and some few state regulation of public utilities regulation: gas pipeline (cf. federal transportation regulation: pipeline)',
        '80320': 'federal and some few state regulation of public utilities regulation: radio and television (cf. cable television)',
        '80330': 'federal and some few state regulation of public utilities regulation: cable television (cf. radio and television)',
        '80340': 'federal and some few state regulations of public utilities regulation: telephone or telegraph company',
        '80350': 'miscellaneous economic regulation',
        '90010': 'comity: civil rights',
        '90020': 'comity: criminal procedure',
        '90030': 'comity: First Amendment',
        '90040': 'comity: habeas corpus',
        '90050': 'comity: military',
        '90060': 'comity: obscenity',
        '90070': 'comity: privacy',
        '90080': 'comity: miscellaneous',
        '90090': 'comity primarily removal cases, civil procedure (cf. comity, criminal and First Amendment); deference to foreign judicial tribunals',
        '90100': 'assessment of costs or damages: as part of a court order',
        '90110': 'Federal Rules of Civil Procedure including Supreme Court Rules, application of the Federal Rules of Evidence, Federal Rules of Appellate Procedure in civil litigation, Circuit Court Rules, and state rules and admiralty rules',
        '90120': "judicial review of administrative agency's or administrative official's actions and procedures",
        '90130': 'mootness (cf. standing to sue: live dispute)',
        '90140': 'venue',
        '90150': 'no merits: writ improvidently granted',
        '90160': 'no merits: dismissed or affirmed for want of a substantial or properly presented federal question, or a nonsuit',
        '90170': 'no merits: dismissed or affirmed for want of jurisdiction (cf. judicial administration: Supreme Court jurisdiction or authority on appeal from federal district courts or courts of appeals)',
        '90180': 'no merits: adequate non-federal grounds for decision',
        '90190': 'no merits: remand to determine basis of state or federal court decision (cf. judicial administration: state law)',
        '90200': 'no merits: miscellaneous',
        '90210': 'standing to sue: adversary parties',
        '90220': 'standing to sue: direct injury',
        '90230': 'standing to sue: legal injury',
        '90240': 'standing to sue: personal injury',
        '90250': 'standing to sue: justiciable question',
        '90260': 'standing to sue: live dispute',
        '90270': 'standing to sue: parens patriae standing',
        '90280': 'standing to sue: statutory standing',
        '90290': 'standing to sue: private or implied cause of action',
        '90300': "standing to sue: taxpayer's suit",
        '90310': 'standing to sue: miscellaneous',
        '90320': 'judicial administration: jurisdiction or authority of federal district courts or territorial courts',
        '90330': 'judicial administration: jurisdiction or authority of federal courts of appeals',
        '90340': 'judicial administration: Supreme Court jurisdiction or authority on appeal or writ of error, from federal district courts or courts of appeals (cf. 753)',
        '90350': 'judicial administration: Supreme Court jurisdiction or authority on appeal or writ of error, from highest state court',
        '90360': 'judicial administration: jurisdiction or authority of the Court of Claims',
        '90370': "judicial administration: Supreme Court's original jurisdiction",
        '90380': 'judicial administration: review of non-final order',
        '90390': 'judicial administration: change in state law (cf. no merits: remand to determine basis of state court decision)',
        '90400': 'judicial administration: federal question (cf. no merits: dismissed for want of a substantial or properly presented federal question)',
        '90410': 'judicial administration: ancillary or pendent jurisdiction',
        '90420': 'judicial administration: extraordinary relief (e.g., mandamus, injunction)',
        '90430': 'judicial administration: certification (cf. objection to reason for denial of certiorari or appeal)',
        '90440': 'judicial administration: resolution of circuit conflict, or conflict between or among other courts',
        '90450': 'judicial administration: objection to reason for denial of certiorari or appeal',
        '90460': 'judicial administration: collateral estoppel or res judicata',
        '90470': 'judicial administration: interpleader',
        '90480': 'judicial administration: untimely filing',
        '90490': 'judicial administration: Act of State doctrine',
        '90500': 'judicial administration: miscellaneous',
        '90510': "Supreme Court's certiorari, writ of error, or appeals jurisdiction",
        '90520': 'miscellaneous judicial power, especially diversity jurisdiction'}

    def __init__(self, data_dir=None, download_if_missing=True):
        if data_dir is None:
            data_dir = __resources_dir__
        self.filepath = os.path.join(data_dir, 'supremecourt', FILENAME)
        if not os.path.exists(self.filepath):
            if download_if_missing is True:
                self._download_data()
            else:
                raise OSError('file "{}" not found'.format(self.filepath))

    def _download_data(self):
        LOGGER.info('downloading data from "%s"', URL)
        response = requests.get(URL)
        make_dirs(self.filepath, 'wb')
        with io.open(self.filepath, mode='wb') as f:
            f.write(response.content)

    def _iterate(self, text_only, date_range=None, min_len=None, limit=-1):
        """Note: Use `.texts()` or `.docs()` to iterate over corpus data."""
        # prepare date range filter
        if date_range:
            if not isinstance(date_range, (list, tuple)):
                raise ValueError('`date_range` must be a list or tuple, not %s', type(date_range))
            if not len(date_range) == 2:
                raise ValueError('`date_range` must have both start and end values')
            if not date_range[0]:
                date_range = (MIN_DATE, date_range[1])
            if not date_range[1]:
                date_range = (date_range[0], MAX_DATE)

        n = 0
        mode = 'rb' if PY2 else 'rt'
        for line in read_json_lines(self.filepath, mode=mode):
            if date_range and not date_range[0] <= line['decided_date'] <= date_range[1]:
                continue
            if min_len and len(line['text']) < min_len:
                continue

            if text_only is True:
                yield line['text']
            else:
                yield line

            n += 1
            if n == limit:
                break

    def texts(self, date_range=None, min_len=None, limit=-1):
        """
        Iterate over texts in the CapitolWords corpus, optionally filtering by
        a variety of metadata and/or text length, in order of date.

        Args:
            date_range (list[str] or tuple[str]): filter speeches by the date on
                which they were given; both start and end date must be specified,
                but a null value for either will be replaced by the min/max date
                available in the corpus
            min_len (int): filter speeches by the length (number of characters)
                in their text content
            limit (int): return no more than `limit` speeches, in order of date

        Yields:
            str: full text of next (by chronological order) speech in corpus
                passing all filter params

        Raises:
            ValueError: if any filtering options are invalid
        """
        texts = self._iterate(
            True, date_range=date_range, min_len=min_len, limit=limit)
        for text in texts:
            yield text

    def docs(self, date_range=None, min_len=None, limit=-1):
        """
        Iterate over documents (including text and metadata) in the CapitolWords
        corpus, optionally filtering by a variety of metadata and/or text length,
        in order of date.

        Args:
            date_range (list[str] or tuple[str]): filter speeches by the date on
                which they were given; both start and end date must be specified,
                but a null value for either will be replaced by the min/max date
                available in the corpus
            min_len (int): filter speeches by the length (number of characters)
                in their text content
            limit (int): return no more than `limit` speeches, in order of date

        Yields:
            dict: full text and metadata of next (by chronological order) speech
                in corpus passing all filter params

        Raises:
            ValueError: if any filtering options are invalid
        """
        docs = self._iterate(
            False, date_range=date_range, min_len=min_len, limit=limit)
        for doc in docs:
            yield doc
