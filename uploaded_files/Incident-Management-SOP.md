# Standard Operating Procedure: Incident Management
**Document ID:** SOP-IT-001  
**Version:** 3.2  
**Effective Date:** December 1, 2024  
**Review Date:** June 1, 2025  
**Department:** IT Operations  
**Owner:** IT Service Management Team

---

## 1. PURPOSE

This Standard Operating Procedure (SOP) defines the processes for identifying, logging, categorizing, prioritizing, resolving, and closing IT incidents to minimize business impact and restore normal service operations quickly.

---

## 2. SCOPE

### 2.1 Applies To
- All IT incidents affecting company services
- All IT support staff (L1, L2, L3)
- Service Desk analysts
- System administrators
- Application support teams

### 2.2 Does Not Apply To
- Scheduled maintenance activities
- Planned system upgrades
- Service requests (use SR process)
- Change requests (use Change Management SOP)

---

## 3. DEFINITIONS

**Incident:** An unplanned interruption or reduction in quality of an IT service.

**Major Incident:** An incident with significant business impact requiring immediate attention and escalation.

**Service Level Agreement (SLA):** Agreed-upon time frames for incident response and resolution.

**Priority:** The urgency and impact combination determining response time.

**Workaround:** A temporary solution that allows service to continue while permanent fix is developed.

---

## 4. INCIDENT CLASSIFICATION

### 4.1 Impact Levels

**Critical (Impact 1):**
- Complete service outage
- Affects entire company or multiple departments
- Examples: Email system down, network outage, ERP system failure

**High (Impact 2):**
- Significant service degradation
- Affects department or team
- Examples: Department printer offline, shared drive inaccessible

**Medium (Impact 3):**
- Limited service impact
- Affects small group (5-10 users)
- Examples: Application performance issues, minor network slowness

**Low (Impact 4):**
- Minimal service impact
- Affects individual user
- Examples: Single PC issue, password reset, software question

### 4.2 Urgency Levels

**Critical:**
- Immediate business impact
- No workaround available
- Regulatory or compliance risk

**High:**
- Significant business impact
- Limited workaround
- Time-sensitive work blocked

**Medium:**
- Moderate business impact
- Workaround available
- Can wait for next business day

**Low:**
- Minor inconvenience
- No immediate business impact
- Can be scheduled

---

## 5. INCIDENT PRIORITY MATRIX

| Impact / Urgency | Critical | High | Medium | Low |
|------------------|----------|------|--------|-----|
| **Critical** | P1 | P1 | P2 | P3 |
| **High** | P1 | P2 | P3 | P4 |
| **Medium** | P2 | P3 | P3 | P4 |
| **Low** | P3 | P4 | P4 | P4 |

---

## 6. SERVICE LEVEL AGREEMENTS (SLAs)

### 6.1 Response Times

| Priority | Response Time | Target Resolution |
|----------|---------------|-------------------|
| **P1 - Critical** | 15 minutes | 4 hours |
| **P2 - High** | 1 hour | 8 hours |
| **P3 - Medium** | 4 hours | 24 hours |
| **P4 - Low** | 8 hours | 72 hours |

### 6.2 Business Hours
- **Standard Support:** Monday-Friday, 8:00 AM - 6:00 PM EST
- **After Hours:** P1 incidents only (24/7 on-call team)
- **Holidays:** P1 incidents only

### 6.3 SLA Clock Rules
- Clock starts when incident is logged
- Clock pauses for "Awaiting User Response"
- Clock stops when incident is resolved
- Major incidents exempt from SLA (best effort)

---

## 7. INCIDENT LIFECYCLE

### 7.1 Phase 1: Detection and Logging

**7.1.1 Incident Detection Methods**
- User-reported (email, phone, chat, self-service portal)
- Automated monitoring alerts
- Service desk proactive monitoring
- Third-party vendor notifications

**7.1.2 Logging Requirements**
All incidents must be logged in ServiceNow with:
- **Requester Information:** Name, department, contact details
- **Incident Description:** Clear, detailed description of issue
- **Business Impact:** How this affects user's work
- **Configuration Item (CI):** Affected system/service
- **Timestamp:** When issue started
- **Error Messages:** Exact error text or screenshots

**7.1.3 Logging Standards**
Good: "User Jane Smith cannot access Salesforce. Error message: 'Invalid username or password.' Last successful login: 12/1/24 9:00 AM. User needs access for client call at 2:00 PM today."

Bad: "Salesforce not working."

### 7.2 Phase 2: Categorization and Prioritization

**7.2.1 Categorization**
Select correct category and subcategory:
- **Hardware:** Desktop, Laptop, Printer, Server, Network Device
- **Software:** Application, Operating System, Email, VPN
- **Network:** Connectivity, Wi-Fi, VPN, Firewall
- **Access:** Password Reset, Account Unlock, Permission Request
- **Security:** Virus/Malware, Phishing, Data Breach

**7.2.2 Priority Assignment**
- Use Priority Matrix (Section 5)
- Consider business impact and urgency
- Escalate if unsure about priority
- Document priority rationale in notes

**7.2.3 Major Incident Identification**
Declare Major Incident if:
- Affects 50+ users or critical business function
- Estimated downtime > 4 hours
- Financial impact > $50,000
- Security breach or data loss
- Regulatory compliance risk

**Major Incident Declaration Process:**
1. Service Desk Supervisor declares major incident
2. Activate Major Incident Response Team
3. Create dedicated Teams channel
4. Notify executive stakeholders
5. Begin regular status updates (every 30 minutes)

### 7.3 Phase 3: Initial Diagnosis

**7.3.1 Information Gathering**
Ask targeted questions:
- When did issue start?
- Has this worked before?
- What changed recently?
- Can you reproduce the issue?
- Is anyone else affected?
- What troubleshooting have you tried?

**7.3.2 Basic Troubleshooting (L1 Service Desk)**
- Verify user identity
- Check system status dashboard
- Review recent changes
- Test from different device/location
- Clear cache/cookies
- Restart application/device
- Check account status

**7.3.3 Remote Support Tools**
Use approved tools only:
- **TeamViewer:** Windows/Mac remote support
- **Microsoft Quick Assist:** Windows built-in
- **Bomgar:** Privileged access for servers
- **AnyDesk:** Emergency backup tool

**Security Note:** Always verify user identity before remote session. Use verbal code verification for sensitive accounts.

### 7.4 Phase 4: Investigation and Diagnosis

**7.4.1 L2 Support Investigation**
Escalate to L2 when:
- L1 troubleshooting exhausted
- Requires elevated permissions
- Needs specialized knowledge
- SLA in danger (< 25% time remaining)

**L2 Investigation Steps:**
1. Review incident history and related incidents
2. Check monitoring systems and logs
3. Replicate issue in test environment
4. Identify root cause
5. Determine resolution approach
6. Document findings in incident notes

**7.4.2 L3/Vendor Escalation**
Escalate to L3 or vendor when:
- Root cause requires development team
- Vendor product issue identified
- Infrastructure change needed
- Security incident confirmed

**7.4.3 Diagnostic Tools**
- **Event Viewer:** Windows system logs
- **Splunk:** Centralized log analysis
- **Wireshark:** Network packet capture
- **Process Monitor:** Real-time system activity
- **SQL Server Profiler:** Database diagnostics

### 7.5 Phase 5: Resolution and Recovery

**7.5.1 Resolution Methods**

**Permanent Fix:**
- Resolves root cause
- Prevents recurrence
- Preferred method

**Workaround:**
- Temporary solution
- Allows business continuity
- Problem ticket created for permanent fix

**Configuration Change:**
- Modify settings
- Update permissions
- Adjust policies

**7.5.2 Solution Documentation**
Document resolution with:
- Root cause identified
- Steps taken to resolve
- Configuration changes made
- Testing performed
- User confirmation received

**7.5.3 Knowledge Base Article**
Create KB article if:
- Incident occurred 3+ times
- Complex resolution steps
- Unique or interesting issue
- Requested by management

**KB Article Template:**
- **Issue Description:** What problem users see
- **Affected Systems:** Where this occurs
- **Root Cause:** Why it happens
- **Resolution Steps:** How to fix (numbered)
- **Testing:** How to verify fix
- **Prevention:** How to avoid in future

### 7.6 Phase 6: Closure

**7.6.1 Pre-Closure Checklist**
- ✅ User confirms issue resolved
- ✅ Resolution tested and verified
- ✅ All incident notes complete
- ✅ Root cause identified
- ✅ KB article created (if applicable)
- ✅ Related incidents linked
- ✅ Time spent recorded accurately

**7.6.2 User Communication**
Send closure email with:
- Incident number and description
- Root cause summary
- Resolution performed
- Prevention tips
- Satisfaction survey link
- Contact info if issue returns

**7.6.3 Final Status Update**
- Set status to "Resolved"
- Complete closure notes
- Record actual vs. estimated time
- Submit for quality review (10% random sample)

### 7.7 Phase 7: Post-Incident Review (Major Incidents Only)

**7.7.1 Post-Incident Review Meeting**
Conduct within 5 business days for Major Incidents:
- Timeline reconstruction
- Root cause analysis
- Response effectiveness evaluation
- Lessons learned
- Action items identified

**7.7.2 Review Attendees**
- Incident Manager
- Technical leads from response team
- Service owners
- Affected business stakeholders

**7.7.3 Deliverables**
- Post-Incident Review Report
- Action item tracker
- Process improvement recommendations
- Updated documentation/procedures

---

## 8. COMMUNICATION GUIDELINES

### 8.1 User Communication Standards

**Initial Response (within SLA):**
"Thank you for contacting IT Support. Your incident INC0012345 has been logged with Priority 2. We are investigating and will provide an update within 1 hour. If urgent, call +1-555-0100."

**Progress Updates:**
- P1: Every 30 minutes
- P2: Every 2 hours
- P3: Daily
- P4: Upon significant progress

**Update Template:**
"Update on incident INC0012345: [Current status]. [Actions taken]. [Next steps]. [Estimated resolution time]. Contact me if questions."

**Resolution Communication:**
"Your incident INC0012345 has been resolved. [Summary of issue]. [Resolution performed]. [Prevention advice]. Please confirm the issue is fully resolved. Thank you for your patience."

### 8.2 Internal Communication

**Team Channel Updates (Major Incidents):**
Post in dedicated Teams channel:
- Status (Red/Yellow/Green)
- Current activity
- Blockers
- ETA to resolution

**Management Updates (Major Incidents):**
Email updates to leadership:
- Executive summary
- Business impact
- Customer-facing impact
- Current status and next steps
- Estimated resolution time

### 8.3 Communication Escalation

**When to Escalate Communication:**
- SLA at risk (< 25% remaining)
- User extremely dissatisfied
- VIP/executive user affected
- Major incident declared
- Media/public attention

**Escalation Contacts:**
- **L1 to L2:** Service Desk Supervisor
- **L2 to L3:** IT Operations Manager
- **Major Incident:** IT Director
- **Critical/VIP:** CIO

---

## 9. ESCALATION PROCEDURES

### 9.1 Technical Escalation

**Level 1 (Service Desk):**
- First point of contact
- Basic troubleshooting
- Password resets, account unlocks
- Known issue resolution
- Ticket routing

**Level 2 (Technical Support):**
- Desktop/laptop hardware
- Application support
- Network connectivity
- Advanced troubleshooting
- On-site support

**Level 3 (Specialists):**
- **Systems Administration:** Servers, Active Directory
- **Network Engineering:** Firewalls, switches, VPN
- **Database Administration:** SQL, Oracle
- **Application Development:** Custom apps, integrations
- **Security Team:** Security incidents, malware

### 9.2 Hierarchical Escalation

**When to Escalate to Management:**
- SLA breach imminent or occurred
- User requesting manager involvement
- Incident requires business decision
- Resource constraints preventing resolution
- Policy exception needed

**Escalation Path:**
1. Service Desk Analyst → Service Desk Supervisor
2. Service Desk Supervisor → IT Operations Manager
3. IT Operations Manager → IT Director
4. IT Director → CIO

### 9.3 Vendor Escalation

**Vendor Support Process:**
1. Verify issue is vendor product-related
2. Gather all diagnostic information
3. Check vendor support portal for known issues
4. Open vendor ticket
5. Document vendor ticket number in ServiceNow
6. Monitor vendor progress
7. Provide vendor updates to user

**Vendor Contact Information:**
- Microsoft: Premier Support Portal
- Cisco: TAC Case Portal
- VMware: Support Request Portal
- Salesforce: Customer Support Portal

---

## 10. SPECIAL INCIDENT TYPES

### 10.1 Security Incidents

**Identification:**
- Malware/virus detected
- Unauthorized access attempt
- Phishing email
- Data breach suspected
- Lost/stolen device

**Process:**
1. Immediately escalate to Security Team
2. Do NOT investigate independently
3. Preserve evidence (do not power off)
4. Document exactly what occurred
5. Isolate affected system if instructed
6. Follow Security Team directives

**Security Team Contact:**
- Email: security-incident@company.com
- Phone: +1-555-0199 (24/7)

### 10.2 VIP User Incidents

**VIP Users:**
- C-level executives
- Board members
- Key customers/partners

**Special Handling:**
- Immediate priority boost (+1 priority level)
- Assign senior technician
- Provide personal attention
- Offer on-site support
- White-glove communication
- Notify IT management

### 10.3 Mass Incidents

**When Multiple Users Report Same Issue:**
1. Identify pattern (same symptoms/service)
2. Log parent incident
3. Link child incidents
4. Communicate via mass notification
5. Update status page
6. Prevent duplicate logging

**Mass Incident Communication:**
"We are aware of an issue affecting [service/system]. Multiple users are impacted. IT is investigating. Updates will be posted on status.company.com every 30 minutes."

### 10.4 After-Hours Incidents

**On-Call Support (P1 Only):**
- Contact on-call engineer via PagerDuty
- 15-minute response time
- Remote resolution preferred
- On-site if critical (1-hour response)

**Non-P1 After Hours:**
- Log ticket in self-service portal
- Will be addressed next business day
- Emergency? Explain business impact for triage

---

## 11. TOOLS AND SYSTEMS

### 11.1 ServiceNow ITSM Platform
- **Purpose:** Incident logging, tracking, reporting
- **URL:** https://company.service-now.com
- **Training:** Required for all support staff
- **Mobile App:** Available for iOS/Android

**Key Features:**
- Automated ticket routing
- SLA tracking and alerts
- Knowledge base integration
- Self-service portal
- Reporting dashboards

### 11.2 Monitoring Systems

**SolarWinds (Infrastructure):**
- Server performance monitoring
- Network device monitoring
- Alert configuration
- Dashboards

**Datadog (Application Performance):**
- Application health monitoring
- User experience tracking
- API monitoring
- Custom metrics

**StatusPage.io (Status Communication):**
- Public status page
- Incident updates
- Maintenance scheduling
- Subscription notifications

### 11.3 Communication Tools

**Microsoft Teams:**
- Primary communication platform
- Incident war rooms
- Screen sharing
- File sharing

**PagerDuty:**
- On-call scheduling
- Incident alerting
- Escalation automation
- Integration with monitoring

---

## 12. METRICS AND REPORTING

### 12.1 Key Performance Indicators (KPIs)

**Volume Metrics:**
- Total incidents logged
- Incidents by category
- Incidents by priority
- Recurring incidents

**Performance Metrics:**
- First Call Resolution (FCR) rate: Target 70%
- SLA compliance: Target 95%
- Average resolution time by priority
- Escalation rate: Target < 15%

**Quality Metrics:**
- Customer satisfaction (CSAT): Target 4.5/5
- Ticket quality score: Target 90%
- Reopened ticket rate: Target < 5%
- Major incident count

### 12.2 Reporting Schedule

**Daily Reports (Auto-generated):**
- Open incidents by priority
- SLA breaches
- Escalated incidents

**Weekly Reports (Supervisor):**
- Team performance summary
- Top issues
- Trend analysis
- Training needs identified

**Monthly Reports (Management):**
- Executive dashboard
- KPI tracking
- Budget impact
- Process improvements

**Quarterly Reports (Leadership):**
- Strategic review
- Capacity planning
- Investment recommendations
- Industry benchmarking

### 12.3 Continuous Improvement

**Monthly Process Review:**
- Identify pain points
- Review major incidents
- Analyze trends
- Implement improvements

**Annual SOP Review:**
- Update procedures
- Incorporate lessons learned
- Technology updates
- Regulatory changes

---

## 13. TRAINING REQUIREMENTS

### 13.1 New Hire Training

**Week 1: Fundamentals**
- ServiceNow basics
- Incident lifecycle
- Communication standards
- Common issues

**Week 2: Technical Skills**
- Remote support tools
- Diagnostic procedures
- Escalation process
- Knowledge base usage

**Week 3: Shadowing**
- Observe senior analysts
- Handle incidents with supervision
- Practice communication
- System familiarity

**Week 4: Independent**
- Handle assigned incidents
- Daily check-ins with mentor
- Performance feedback
- Certification preparation

### 13.2 Ongoing Training

**Monthly Training Sessions:**
- New products/features
- Common issues review
- Customer service skills
- Technical deep dives

**Annual Certifications:**
- ITIL Foundation (required)
- HDI Support Center Analyst (recommended)
- Microsoft/Cisco certifications (role-specific)

**Skills Assessment:**
- Quarterly technical tests
- Annual performance review
- Customer feedback review
- Career development planning

---

## 14. QUALITY ASSURANCE

### 14.1 Ticket Quality Review

**Random Sample Review (10%):**
- Proper categorization
- Complete documentation
- Resolution verification
- Communication quality
- SLA compliance

**Quality Criteria:**
- Description clarity: 3 points
- Resolution documentation: 3 points
- Communication professionalism: 2 points
- SLA adherence: 2 points
- Total: 10 points (9+ = Pass)

### 14.2 Customer Satisfaction Surveys

**Survey Distribution:**
- Auto-sent upon ticket closure
- 5-question format
- 5-point scale
- Optional comments

**Survey Questions:**
1. How satisfied are you with the resolution? (1-5)
2. Was the issue resolved in a timely manner? (1-5)
3. How would you rate the technician's professionalism? (1-5)
4. Was the communication clear and helpful? (1-5)
5. How likely are you to recommend IT Support? (1-5)

**Response Handling:**
- CSAT < 3: Manager follows up within 24 hours
- Positive feedback: Shared with team
- Constructive feedback: Used for coaching

### 14.3 Continuous Monitoring

**Live Dashboard Monitoring:**
- Queue depth (Target: < 10 at all times)
- Oldest ticket age (Target: < 4 hours unassigned)
- SLA compliance (Real-time alerts)
- Technician availability

**Automated Alerts:**
- P1 incident created
- SLA breach imminent (< 15 min)
- Queue depth exceeds threshold
- Technician not responding

---

## 15. APPENDICES

### 15.1 Common Issues Quick Reference

**Issue: User Cannot Log In**
1. Verify username spelling
2. Check Caps Lock
3. Try password reset
4. Check account status (locked/disabled)
5. Test from another device

**Issue: Email Not Working**
1. Check internet connectivity
2. Verify Outlook version
3. Test webmail (OWA)
4. Check mailbox quota
5. Review send/receive errors

**Issue: Printer Not Working**
1. Check power and connections
2. Verify print queue
3. Test with another document
4. Check printer status
4. Restart print spooler service

**Issue: Application Slow**
1. Check user's internet speed
2. Verify application status
3. Test from another location
4. Check for recent updates
5. Review application logs

### 15.2 Escalation Contact List

| Team | Email | Phone | Hours |
|------|-------|-------|-------|
| Service Desk | helpdesk@company.com | +1-555-0100 | 8AM-6PM EST |
| Desktop Support | desktop@company.com | +1-555-0101 | 8AM-6PM EST |
| Network Team | network@company.com | +1-555-0102 | 8AM-6PM EST |
| Security Team | security@company.com | +1-555-0199 | 24/7 |
| Database Team | dba@company.com | +1-555-0103 | 8AM-6PM EST |
| After Hours | oncall@company.com | PagerDuty | 24/7 (P1 only) |

### 15.3 Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Jan 2020 | J. Smith | Initial SOP |
| 2.0 | Jun 2022 | M. Johnson | Major revision, added KPIs |
| 3.0 | Jan 2024 | R. Williams | Updated tools, added security |
| 3.1 | Jun 2024 | R. Williams | SLA adjustments, VIP process |
| 3.2 | Dec 2024 | R. Williams | Quality assurance section |

---

## 16. APPROVAL

This SOP has been reviewed and approved by:

**IT Operations Manager:** Robert Williams  
**Date:** December 1, 2024  
**Signature:** _________________

**IT Director:** Michelle Chen  
**Date:** December 1, 2024  
**Signature:** _________________

**Chief Information Officer:** David Park  
**Date:** December 1, 2024  
**Signature:** _________________

---

*End of SOP*

**Next Review Date:** June 1, 2025

**Document Location:** SharePoint > IT Department > SOPs > Incident Management

**Questions?** Contact: itsm@company.com
