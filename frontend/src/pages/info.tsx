import { Link } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Mail, ShieldCheck, Trophy } from "lucide-react";

const content: Record<string, { title: string; subtitle: string; sections: { heading: string; body: string }[] }> = {
  about: {
    title: "About VIT Sports Intelligence Network",
    subtitle: "A sports intelligence platform combining ML predictions, analyst training, VITCoin incentives, and transparent marketplace economics.",
    sections: [
      { heading: "Mission", body: "VIT helps sports analysts, developers, and validators collaborate around measurable prediction intelligence instead of opaque tips or unverifiable claims." },
      { heading: "Platform", body: "The network includes a 12-model prediction ensemble, analyst training workflows, marketplace listings, wallet rewards, governance, and safety controls." },
      { heading: "Marketplace", body: "Developers can submit model packages for review, and approved models can earn VITCoin when used or trained through supported platform flows." },
    ],
  },
  terms: {
    title: "Terms & Conditions",
    subtitle: "Rules for using VIT Sports Intelligence Network.",
    sections: [
      { heading: "Eligibility", body: "You are responsible for complying with local laws and must not use the platform where sports prediction, token rewards, or related services are restricted." },
      { heading: "No guaranteed outcomes", body: "Predictions, odds intelligence, and model outputs are informational only. VIT does not guarantee profit, accuracy, or betting outcomes." },
      { heading: "Marketplace submissions", body: "Model creators must own or have rights to uploaded files. Submissions may be reviewed, rejected, suspended, or removed for safety, quality, or compliance reasons." },
      { heading: "Rewards and fees", body: "VITCoin rewards, listing fees, call fees, and protocol shares may change through platform configuration or governance decisions." },
      { heading: "Account safety", body: "Users must protect credentials, avoid abuse, and not upload malicious code, stolen data, or artifacts that violate third-party rights." },
    ],
  },
  privacy: {
    title: "Privacy Policy",
    subtitle: "How VIT handles account, marketplace, and training data.",
    sections: [
      { heading: "Data collected", body: "VIT may process account details, wallet activity, predictions, training activity, marketplace submissions, usage logs, ratings, and support messages." },
      { heading: "Data use", body: "Data is used to operate the platform, secure accounts, calculate rewards, review marketplace submissions, improve model performance, and provide support." },
      { heading: "Model uploads", body: "Uploaded model files and metadata are stored for review, approval, operation, audit, and abuse prevention." },
      { heading: "User choices", body: "Users can update account settings, request support, and should avoid uploading sensitive personal information inside model artifacts." },
    ],
  },
  contact: {
    title: "Contact",
    subtitle: "Reach the VIT team for marketplace, account, legal, or partnership support.",
    sections: [
      { heading: "Support", body: "For account, wallet, prediction, or marketplace issues, contact support@vit.network with your username and a clear description of the issue." },
      { heading: "Legal", body: "For legal, compliance, or takedown notices, contact legal@vit.network and include the affected listing, content, or account details." },
      { heading: "Developers", body: "For model onboarding or API questions, use the Developer section in the app and include your intended system model slot and package format." },
    ],
  },
};

export default function InfoPage({ type }: { type: keyof typeof content }) {
  const page = content[type] ?? content.about;
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border/60 px-4 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link href="/">
            <span className="flex cursor-pointer items-center gap-2 font-mono font-bold">
              <Trophy className="h-5 w-5 text-primary" /> VIT Network
            </span>
          </Link>
          <Link href="/login"><Button size="sm">Open App</Button></Link>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-10">
        <div className="mb-8 max-w-3xl">
          <div className="mb-3 flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-primary">
            {type === "contact" ? <Mail className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}
            VIT information
          </div>
          <h1 className="text-3xl font-bold md:text-4xl">{page.title}</h1>
          <p className="mt-3 text-muted-foreground">{page.subtitle}</p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {page.sections.map((section) => (
              <section key={section.heading}>
                <h2 className="mb-2 text-lg font-semibold">{section.heading}</h2>
                <p className="text-sm leading-6 text-muted-foreground">{section.body}</p>
              </section>
            ))}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}