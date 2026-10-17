"""Diagnostics must require consent, protect privacy, and fail without breaking BBE."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ADDON=Path(__file__).resolve().parents[1]/'src/addons/no_mans_sky_base_builder'
sys.path.insert(0,str(ADDON))
import blender_diagnostics as diagnostics
import furby_errors as errors

class DiagnosticsTests(unittest.TestCase):
    def payload(self):
        return dict(report_id='a'*32,app='bbe',version='18.1.82',title='Example failure',description='File "C:\\Users\\Example\\source.py"\npassword=secret\nuser@example.com',environment='Windows / Blender 5.2.2',createdUtc='2026-10-17T12:00:00Z',email='never send',save='never send')

    def test_offline_and_no_consent_never_launch_network_worker(self):
        client=diagnostics.DiagnosticClient()
        with patch.object(diagnostics.subprocess,'Popen') as spawn:
            for consent,online in [(False,True),(True,False),(False,False)]:
                with self.assertRaises(ValueError):client.start(self.payload(),consent=consent,online=online)
            spawn.assert_not_called()
        self.assertFalse(client.busy)

    def test_only_redacted_allowlisted_fields_are_submitted(self):
        data=diagnostics.prepare(self.payload())
        self.assertNotIn('email',data);self.assertNotIn('save',data)
        self.assertNotIn('Example\\',data['description']);self.assertNotIn('secret',data['description']);self.assertNotIn('user@example.com',data['description'])
        self.assertEqual(data['report_id'],'a'*32)
        self.assertTrue(data['consent'])
        large=self.payload();large['description']='紫'*10000
        self.assertLess(len(json.dumps(diagnostics.prepare(large),ensure_ascii=False).encode()),32000)

    def test_handled_error_is_logged_with_traceback_and_no_upload(self):
        with tempfile.TemporaryDirectory() as folder:
            reporter=errors.ErrorReporter('bbe','18.1.82','Windows',directory=folder)
            operator=Mock(bl_label='Ship Management');previous=errors._active_reporter
            try:
                errors._active_reporter=reporter
                try:raise ValueError('Broken link')
                except ValueError:errors.report_error(operator,{'ERROR'},'Could not open')
                operator.report.assert_called_once_with({'ERROR'},'Could not open')
                self.assertIn('Traceback',reporter.latest['description'])
                self.assertEqual(len(reporter.latest['report_id']),32)
                self.assertEqual(reporter.queue.qsize(),1)
                reporter.record('Ship Management',reporter.latest['description'])
                self.assertEqual(reporter.queue.qsize(),1)
            finally:errors._active_reporter=previous;reporter.close()

    def test_send_validates_receipt_and_rejects_redirects(self):
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.status=201
        response.read.return_value=json.dumps({'ok':True,'diagnosticsOnly':True,'id':'b'*24}).encode()
        opener=Mock();opener.open.return_value=response
        with patch.object(diagnostics.urllib.request,'build_opener',return_value=opener):
            self.assertEqual(diagnostics.send(self.payload()),'b'*24)
            request=opener.open.call_args.args[0]
            self.assertEqual(request.full_url,diagnostics.ENDPOINT)
            self.assertNotIn('Cookie',request.headers)
            response.read.return_value=b'{"ok":true}'
            with self.assertRaises(ValueError):diagnostics.send(self.payload())
        with self.assertRaises(ValueError):diagnostics.NoRedirect().redirect_request(None,None,302,'',{},'https://elsewhere.example')

    def test_worker_failure_is_local_and_retry_reuses_identifier(self):
        client=diagnostics.DiagnosticClient();payload=self.payload()
        fake=Mock();fake.poll.return_value=0
        with patch.object(diagnostics.subprocess,'Popen',return_value=fake):
            client.start(payload,consent=True,online=True)
            request=json.loads((client.job/'request.json').read_text());self.assertEqual(request['report_id'],payload['report_id'])
            client.poll(online=True);self.assertIn('kept locally',client.message);self.assertFalse(client.busy)
            client.start(payload,consent=True,online=True)
            (client.job/'result.json').write_text(json.dumps({'id':'b'*24}))
            client.poll(online=True);self.assertIn('Diagnostic sent',client.message)
            client.start(payload,consent=True,online=True);self.assertIn('already sent',client.message);self.assertFalse(client.busy)

    def test_disabling_online_access_stops_active_helper(self):
        client=diagnostics.DiagnosticClient();fake=Mock();fake.poll.return_value=None
        with patch.object(diagnostics.subprocess,'Popen',return_value=fake):
            client.start(self.payload(),consent=True,online=True)
            client.poll(online=False)
        fake.terminate.assert_called_once();self.assertFalse(client.busy);self.assertIsNone(client.job)

if __name__=='__main__':unittest.main()
