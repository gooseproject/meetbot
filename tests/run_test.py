# Richard Darst, 2009

import glob
import os
import re
import shutil
import sys
import tempfile
import unittest

os.environ['MEETBOT_RUNNING_TESTS'] = '1'
import ircmeeting.meeting as meeting
import ircmeeting.writers as writers

running_tests = True

def process_meeting(contents, extraConfig={}, dontSave=True,
                    filename='/dev/null'):
    """Take a test script, return Meeting object of that meeting.

    To access the results (a dict keyed by extensions), use M.save(),
    with M being the return of this function.
    """
    return meeting.process_meeting(contents=contents,
                                channel="#none",  filename=filename,
                                dontSave=dontSave, safeMode=False,
                                extraConfig=extraConfig)

class MeetBotTest(unittest.TestCase):

    def test_replay(self):
        """Replay of a meeting, using 'meeting.py replay'.
        """
        old_argv = sys.argv[:]
        sys.argv[1:] = ["replay", "test-script-1.log.txt"]
        sys.path.insert(0, "../ircmeeting")
        try:
            gbls = {"__name__":"__main__",
                    "__file__":"../ircmeeting/meeting.py"}
            execfile("../ircmeeting/meeting.py", gbls)
            assert "M" in gbls, "M object not in globals: did it run?"
        finally:
            del sys.path[0]
            sys.argv[:] = old_argv

    def test_supybottests(self):
        """Test by sending input to supybot, check responses.

        Uses the external supybot-test command.  Unfortunantly, that
        doesn't have a useful status code, so I need to parse the
        output.
        """
        os.symlink("../MeetBot", "MeetBot")
        os.symlink("../ircmeeting", "ircmeeting")
        sys.path.insert(0, ".")
        try:
            output = os.popen("supybot-test ./MeetBot 2>&1").read()
            assert 'FAILED' not in output, "supybot-based tests failed."
            assert '\nOK\n'     in output, "supybot-based tests failed."
        finally:
            os.unlink("MeetBot")
            os.unlink("ircmeeting")
            del sys.path[0]

    trivial_contents = """
    10:10:10 <x> #startmeeting
    10:10:10 <x> blah
    10:10:10 <x> #endmeeting
    """

    full_writer_map = {
        '.log.txt':     writers.TextLog,
        '.log.1.html':  writers.HTMLlog1,
        '.log.html':    writers.HTMLlog2,
        '.1.html':      writers.HTML1,
        '.html':        writers.HTML2,
        '.rst':         writers.ReST,
        '.rst.html':    writers.HTMLfromReST,
        '.txt':         writers.Text,
        '.mw':          writers.MediaWiki,
        '.pmw':         writers.PmWiki,
        '.tmp.txt|template=+template.txt':   writers.Template,
        '.tmp.html|template=+template.html': writers.Template,
        }

    def M_trivial(self, contents=None, extraConfig={}):
        """Convenience wrapper to process_meeting.
        """
        if contents is None:
            contents = self.trivial_contents
        return process_meeting(contents=contents,
                               extraConfig=extraConfig)

    def test_script_1(self):
        """Run test-script-1.log.txt through the processor.

        - Check all writers
        - Check actual file writing.
        """
        tmpdir = tempfile.mkdtemp(prefix='test-meetbot')
        try:
            process_meeting(contents=file('test-script-1.log.txt').read(),
                            filename=os.path.join(tmpdir, 'meeting'),
                            dontSave=False,
                            extraConfig={'writer_map':self.full_writer_map,
                                         })
            # Test every extension in the full_writer_map to make sure
            # it was written.
            for extension in self.full_writer_map:
                ext = re.search(r'^\.(.*?)($|\|)', extension).group(1)
                files = glob.glob(os.path.join(tmpdir, 'meeting.'+ext))
                assert len(files) > 0, \
                       "Extension did not produce output: '%s'"%extension
        finally:
            shutil.rmtree(tmpdir)

    #def test_script_3(self):
    #   process_meeting(contents=file('test-script-3.log.txt').read(),
    #                   extraConfig={'writer_map':self.full_writer_map})

    all_commands_test_contents = """
    10:10:10 <x> #startmeeting
    10:10:10 <x> #topic h6k4orkac
    10:10:10 <x> #info blaoulrao
    10:10:10 <x> #idea alrkkcao4
    10:10:10 <x> #help ntoircoa5
    10:10:10 <x> #link http://bnatorkcao.net kroacaonteu
    10:10:10 <x> http://jrotjkor.net krotroun
    10:10:10 <x> #action xrceoukrc
    10:10:10 <x> #nick okbtrokr

    # Should not appear in non-log output
    10:10:10 <x> #idea ckmorkont
    10:10:10 <x> #undo

    # Assert that chairs can change the topic, and non-chairs can't.
    10:10:10 <x> #chair y
    10:10:10 <y> #topic topic_doeschange
    10:10:10 <z> #topic topic_doesntchange
    10:10:10 <x> #unchair y
    10:10:10 <y> #topic topic_doesnt2change

    10:10:10 <x> #endmeeting
    """
    def test_contents_test2(self):
        """Ensure that certain input lines do appear in the output.

        This test ensures that the input to certain commands does
        appear in the output.
        """
        M = process_meeting(contents=self.all_commands_test_contents,
                            extraConfig={'writer_map':self.full_writer_map})
        results = M.save()
        for name, output in results.iteritems():
            self.assert_('h6k4orkac' in output, "Topic failed for %s"%name)
            self.assert_('blaoulrao' in output, "Info failed for %s"%name)
            self.assert_('alrkkcao4' in output, "Idea failed for %s"%name)
            self.assert_('ntoircoa5' in output, "Help failed for %s"%name)
            self.assert_('http://bnatorkcao.net' in output,
                                                  "Link(1) failed for %s"%name)
            self.assert_('kroacaonteu' in output, "Link(2) failed for %s"%name)
            self.assert_('http://jrotjkor.net' in output,
                                        "Link detection(1) failed for %s"%name)
            self.assert_('krotroun' in output,
                                        "Link detection(2) failed for %s"%name)
            self.assert_('xrceoukrc' in output, "Action failed for %s"%name)
            self.assert_('okbtrokr' in output, "Nick failed for %s"%name)

            # Things which should only appear or not appear in the
            # notes (not the logs):
            if 'log' not in name:
                self.assert_( 'ckmorkont' not in output,
                              "Undo failed for %s"%name)
                self.assert_('topic_doeschange' in output,
                             "Chair changing topic failed for %s"%name)
                self.assert_('topic_doesntchange' not in output,
                             "Non-chair not changing topic failed for %s"%name)
                self.assert_('topic_doesnt2change' not in output,
                            "Un-chaired was able to chang topic for %s"%name)

    #def test_contents_test(self):
    #    contents = open('test-script-3.log.txt').read()
    #    M = process_meeting(contents=file('test-script-3.log.txt').read(),
    #                        extraConfig={'writer_map':self.full_writer_map})
    #    results = M.save()
    #    for line in contents.split('\n'):
    #        m = re.search(r'#(\w+)\s+(.*)', line)
    #        if not m:
    #            continue
    #        type_ = m.group(1)
    #        text = m.group(2)
    #        text = re.sub('[^\w]+', '', text).lower()
    #
    #        m2 = re.search(t2, re.sub(r'[^\w\n]', '', results['.txt']))
    #        import fitz.interactnow
    #        print m.groups()

    def test_actionNickMatching(self):
        """Test properly detect nicknames in lines

        This checks the 'Action items, per person' list to make sure
        that the nick matching is limited to full words.  For example,
        the nick 'jon' will no longer be assigned lines containing
        'jonathan'.
        """
        script = """
        20:13:50 <x> #startmeeting
        20:13:50 <somenick>
        20:13:50 <someone> #action say somenickLONG
        20:13:50 <someone> #action say the somenicklong
        20:13:50 <somenick> I should not have an item assisgned to me.
        20:13:50 <somenicklong> I should have some things assigned to me.
        20:13:50 <x> #endmeeting
        """
        M = process_meeting(script)
        results = M.save()['.html']
        # This regular expression is:
        # \bsomenick\b   - the nick in a single word
        # (?! \()        - without " (" following it... to not match
        #                  the "People present" section.
        assert not re.search(r'\bsomenick\b(?! \()',
                         results, re.IGNORECASE), \
                         "Nick full-word matching failed"

    def test_urlMatching(self):
        """Test properly detection of URLs in lines
        """
        script = """
        20:13:50 <x> #startmeeting
        20:13:50 <x> #link prefix http://site1.com suffix
        20:13:50 <x> http://site2.com suffix
        20:13:50 <x> ftp://ftpsite1.com suffix
        20:13:50 <x> #link prefix ftp://ftpsite2.com suffix
        20:13:50 <x> irc://ircsite1.com suffix
        20:13:50 <x> mailto://a@mail.com suffix
        20:13:50 <x> #endmeeting
        """
        M = process_meeting(script)
        results = M.save()['.html']
        assert re.search(r'prefix.*href.*http://site1.com.*suffix',
                         results), "URL missing 1"
        assert re.search(r'href.*http://site2.com.*suffix',
                         results), "URL missing 2"
        assert re.search(r'href.*ftp://ftpsite1.com.*suffix',
                         results), "URL missing 3"
        assert re.search(r'prefix.*href.*ftp://ftpsite2.com.*suffix',
                         results), "URL missing 4"
        assert re.search(r'href.*mailto://a@mail.com.*suffix',
                         results), "URL missing 5"

    def t_css(self):
        """Runs all CSS-related tests.
        """
        self.test_css_embed()
        self.test_css_noembed()
        self.test_css_file_embed()
        self.test_css_file()
        self.test_css_none()
    def test_css_embed(self):
        extraConfig={ }
        results = self.M_trivial(extraConfig={}).save()
        self.assert_('<link rel="stylesheet" ' not in results['.html'])
        self.assert_('body {'                      in results['.html'])
        self.assert_('<link rel="stylesheet" ' not in results['.log.html'])
        self.assert_('body {'                      in results['.log.html'])
    def test_css_noembed(self):
        extraConfig={'cssEmbed_minutes':False,
                     'cssEmbed_log':False,}
        M = self.M_trivial(extraConfig=extraConfig)
        results = M.save()
        self.assert_('<link rel="stylesheet" '     in results['.html'])
        self.assert_('body {'                  not in results['.html'])
        self.assert_('<link rel="stylesheet" '     in results['.log.html'])
        self.assert_('body {'                  not in results['.log.html'])
    def test_css_file(self):
        tmpf = tempfile.NamedTemporaryFile()
        magic_string = '546uorck6o45tuo6'
        tmpf.write(magic_string)
        tmpf.flush()
        extraConfig={'cssFile_minutes':  tmpf.name,
                     'cssFile_log':      tmpf.name,}
        M = self.M_trivial(extraConfig=extraConfig)
        results = M.save()
        self.assert_('<link rel="stylesheet" ' not in results['.html'])
        self.assert_(magic_string                  in results['.html'])
        self.assert_('<link rel="stylesheet" ' not in results['.log.html'])
        self.assert_(magic_string                  in results['.log.html'])
    def test_css_file_embed(self):
        tmpf = tempfile.NamedTemporaryFile()
        magic_string = '546uorck6o45tuo6'
        tmpf.write(magic_string)
        tmpf.flush()
        extraConfig={'cssFile_minutes':  tmpf.name,
                     'cssFile_log':      tmpf.name,
                     'cssEmbed_minutes': False,
                     'cssEmbed_log':     False,}
        M = self.M_trivial(extraConfig=extraConfig)
        results = M.save()
        self.assert_('<link rel="stylesheet" '     in results['.html'])
        self.assert_(tmpf.name                     in results['.html'])
        self.assert_('<link rel="stylesheet" '     in results['.log.html'])
        self.assert_(tmpf.name                     in results['.log.html'])
    def test_css_none(self):
        tmpf = tempfile.NamedTemporaryFile()
        magic_string = '546uorck6o45tuo6'
        tmpf.write(magic_string)
        tmpf.flush()
        extraConfig={'cssFile_minutes':  'none',
                     'cssFile_log':      'none',}
        M = self.M_trivial(extraConfig=extraConfig)
        results = M.save()
        self.assert_('<link rel="stylesheet" ' not in results['.html'])
        self.assert_('<style type="text/css" ' not in results['.html'])
        self.assert_('<link rel="stylesheet" ' not in results['.log.html'])
        self.assert_('<style type="text/css" ' not in results['.log.html'])

    def test_filenamevars(self):
        def getM(fnamepattern):
            M = meeting.Meeting(channel='somechannel',
                                network='somenetwork',
                                owner='nobody',
                     extraConfig={'filenamePattern':fnamepattern})
            M.addline('nobody', '#startmeeting')
            return M
        # Test the %(channel)s and %(network)s commands in supybot.
        M = getM('%(channel)s-%(network)s')
        assert M.config.filename().endswith('somechannel-somenetwork'), \
               "Filename not as expected: "+M.config.filename()
        # Test dates in filenames
        M = getM('%(channel)s-%%F')
        import time
        assert M.config.filename().endswith(time.strftime('somechannel-%F')),\
               "Filename not as expected: "+M.config.filename()
        # Test #meetingname in filenames
        M = getM('%(channel)s-%(meetingname)s')
        M.addline('nobody', '#meetingname blah1234')
        assert M.config.filename().endswith('somechannel-blah1234'),\
               "Filename not as expected: "+M.config.filename()


if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(__file__), '.'))
    if len(sys.argv) <= 1:
        unittest.main()
    else:
        for testname in sys.argv[1:]:
            print testname
            if hasattr(MeetBotTest, testname):
                MeetBotTest(methodName=testname).debug()
            else:
                MeetBotTest(methodName='test_'+testname).debug()

