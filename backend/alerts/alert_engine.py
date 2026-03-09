import logging

logger = logging.getLogger(__name__)

class AlertEngine:
    def __init__(self):
        self.webhook_url = None
        self.smtp_config = None

    def process_anomalies(self, anomalies):
        """
        Takes in a list of detected anomalies and generates alert payloads 
        to theoretically push to Slack/Email.
        """
        alerts_sent = []
        
        for anomaly in anomalies:
            if not anomaly.get('is_anomaly'):
                 continue
                 
            # Extract
            svc = anomaly.get('service_name', 'Global Resources')
            actual = anomaly.get('cost', 0.0)
            expected = anomaly.get('expected_cost', 0.0)
            severity = anomaly.get('severity', 'low')
            
            # Formulate
            alert_payload = {
                "type": "Cost Spike",
                "service": svc,
                "expected": expected,
                "actual": actual,
                "severity": severity,
                "message": f"CRITICAL: {svc} spiked to ${actual} (Expected: ~${expected})"
            }
            
            # Send Notification Route
            self._dispatch_slack(alert_payload)
            self._dispatch_email(alert_payload)
            
            alerts_sent.append(alert_payload)
            
        return alerts_sent
        
    def _dispatch_slack(self, payload):
         # Mock implementation of slack requests.post
         logger.info(f"SLACK NOTIFICATION SENT: {payload['message']}")
         
    def _dispatch_email(self, payload):
         # Mock implementation of SMTP transmission
         logger.info(f"EMAIL NOTIFICATION SENT: {payload['message']}")
