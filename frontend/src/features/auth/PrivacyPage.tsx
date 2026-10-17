import { Link } from "react-router-dom";

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-prose px-6 py-16">
      <h1 className="text-2xl font-semibold text-text-primary">Privacy Policy</h1>
      <p className="mt-2 text-xs text-text-tertiary">
        Effective date: [EFFECTIVE_DATE] | Last updated: [LAST_UPDATED_DATE]
      </p>

      {/* Table of contents */}
      <nav className="mt-8 rounded-md border border-border-default bg-bg-secondary p-6">
        <p className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-3">Contents</p>
        <ol className="list-decimal list-inside space-y-1 text-sm text-accent">
          <li><a href="#information-collected">Information collected</a></li>
          <li><a href="#how-used">How information is used</a></li>
          <li><a href="#legal-bases">Legal bases for processing</a></li>
          <li><a href="#cookies">Cookies and local storage</a></li>
          <li><a href="#third-party">Third-party processors</a></li>
          <li><a href="#retention">Data retention</a></li>
          <li><a href="#security">Security measures</a></li>
          <li><a href="#user-rights">Your rights</a></li>
          <li><a href="#children">Children's privacy</a></li>
          <li><a href="#transfers">International transfers</a></li>
          <li><a href="#changes">Changes to this policy</a></li>
          <li><a href="#contact">Contact</a></li>
        </ol>
      </nav>

      <div className="mt-8 space-y-8 text-sm leading-relaxed text-text-secondary">
        <p>[COMPANY_NAME] ("we", "our", "us") operates the Rosetta application. This Privacy Policy describes how we collect, use, and protect your information when you use our service.</p>

        <section id="information-collected">
          <h2 className="text-lg font-medium text-text-primary mb-2">1. Information collected</h2>
          <p className="mb-2"><strong className="text-text-primary">Account information:</strong> When you create an account, we collect your email address and a hashed password (managed by Supabase Auth). You may optionally provide a display name.</p>
          <p className="mb-2"><strong className="text-text-primary">Code submissions:</strong> When you use the translation feature, we receive and store the source code you submit, the translated output, the languages selected, and metadata such as timestamps and token counts.</p>
          <p><strong className="text-text-primary">Usage data:</strong> We track the number of translations performed per month for quota enforcement. We log request metadata (timestamps, response codes) for operational monitoring. We do not track your browsing activity across other websites.</p>
        </section>

        <section id="how-used">
          <h2 className="text-lg font-medium text-text-primary mb-2">2. How information is used</h2>
          <ul className="list-disc list-inside space-y-1">
            <li>To provide the code translation service</li>
            <li>To maintain your translation history</li>
            <li>To enforce usage limits</li>
            <li>To improve the quality of translations</li>
            <li>To send transactional emails (password resets, account confirmations)</li>
            <li>To detect and prevent abuse</li>
          </ul>
        </section>

        <section id="legal-bases">
          <h2 className="text-lg font-medium text-text-primary mb-2">3. Legal bases for processing</h2>
          <p>We process your data based on: (a) your consent when creating an account, (b) contractual necessity to provide the service, and (c) legitimate interest in maintaining security and preventing abuse.</p>
        </section>

        <section id="cookies">
          <h2 className="text-lg font-medium text-text-primary mb-2">4. Cookies and local storage</h2>
          <p>Rosetta uses browser local storage to persist your authentication session and your theme preference (light or dark mode). We do not use tracking cookies, analytics cookies, or advertising cookies.</p>
        </section>

        <section id="third-party">
          <h2 className="text-lg font-medium text-text-primary mb-2">5. Third-party processors</h2>
          <p className="mb-2">We share data with the following third-party services as necessary to operate Rosetta:</p>
          <ul className="list-disc list-inside space-y-1">
            <li><strong className="text-text-primary">Supabase:</strong> Provides authentication, database hosting (PostgreSQL), and file storage. Your account data and translation records are stored on Supabase infrastructure. <a href="https://supabase.com/privacy" className="text-accent hover:text-accent-hover" target="_blank" rel="noopener noreferrer">Supabase Privacy Policy</a></li>
            <li><strong className="text-text-primary">Google (Gemini API):</strong> Your submitted source code is sent to the Google Gemini API for translation. Google processes this data according to their API terms. <a href="https://ai.google.dev/terms" className="text-accent hover:text-accent-hover" target="_blank" rel="noopener noreferrer">Google AI Terms</a></li>
          </ul>
        </section>

        <section id="retention">
          <h2 className="text-lg font-medium text-text-primary mb-2">6. Data retention</h2>
          <p>Your account data and translation history are retained for as long as your account is active. If you delete your account, all associated data is permanently deleted within 30 days. Usage records are retained in aggregate form for operational purposes.</p>
        </section>

        <section id="security">
          <h2 className="text-lg font-medium text-text-primary mb-2">7. Security measures</h2>
          <p>We use TLS encryption for all data in transit. Database access is restricted by row-level security policies. API keys and secrets are stored as environment variables and never committed to source control. Authentication tokens are signed with industry-standard algorithms (HS256).</p>
        </section>

        <section id="user-rights">
          <h2 className="text-lg font-medium text-text-primary mb-2">8. Your rights</h2>
          <p className="mb-2">You have the right to:</p>
          <ul className="list-disc list-inside space-y-1">
            <li><strong className="text-text-primary">Access:</strong> View your account information and translation history through the application</li>
            <li><strong className="text-text-primary">Correction:</strong> Update your display name through the Settings page</li>
            <li><strong className="text-text-primary">Deletion:</strong> Delete your account and all associated data through the Settings page</li>
            <li><strong className="text-text-primary">Export:</strong> Download individual translations through the application</li>
          </ul>
          <p className="mt-2">To exercise these rights or for requests we cannot fulfill through the application, contact us at [CONTACT_EMAIL].</p>
        </section>

        <section id="children">
          <h2 className="text-lg font-medium text-text-primary mb-2">9. Children's privacy</h2>
          <p>Rosetta is not intended for use by individuals under the age of 13. We do not knowingly collect personal information from children. If we become aware that we have collected data from a child under 13, we will delete that data promptly.</p>
        </section>

        <section id="transfers">
          <h2 className="text-lg font-medium text-text-primary mb-2">10. International transfers</h2>
          <p>Your data may be processed in countries other than your own, as our third-party processors (Supabase and Google) operate globally. These transfers are governed by the processors' own data protection agreements and applicable transfer mechanisms.</p>
        </section>

        <section id="changes">
          <h2 className="text-lg font-medium text-text-primary mb-2">11. Changes to this policy</h2>
          <p>We may update this Privacy Policy from time to time. When we do, we will revise the "Last updated" date at the top of this page. For material changes, we will notify you via email or a notice within the application.</p>
        </section>

        <section id="contact">
          <h2 className="text-lg font-medium text-text-primary mb-2">12. Contact</h2>
          <p>If you have questions about this Privacy Policy, contact us at:</p>
          <p className="mt-2">[COMPANY_NAME]<br />[COMPANY_ADDRESS]<br />[CONTACT_EMAIL]</p>
        </section>
      </div>

      <div className="mt-12 border-t border-border-default pt-6">
        <Link to="/" className="text-sm text-accent hover:text-accent-hover">Back to home</Link>
      </div>
    </div>
  );
}
