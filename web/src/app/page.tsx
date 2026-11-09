import Image from "next/image";
import Link from "next/link";
import { CAPTION } from "@/lib/api";
import styles from "./page.module.css";

export default function LandingPage() {
  return (
    <main className={styles.hero}>
      <div className={styles.copy}>
        <Image
          className={styles.logo}
          src="/ucm/ucm-logo.webp"
          alt="University of Central Missouri"
          width={340}
          height={178}
          priority
        />
        <p className={styles.mules}>Academic Catalog Desk</p>
        <h1 className={styles.product}>CampusAsk</h1>
        <p className={styles.headline}>{CAPTION}</p>
        <p className={styles.support}>
          Every reply cites official catalog evidence—or clearly abstains.
        </p>
        <Link className={styles.cta} href="/ask">
          Ask CampusAsk
        </Link>
        <p className={styles.footnote}>
          Indexed Undergraduate &amp; Graduate Catalogs and Registrar guidance.
        </p>
      </div>
    </main>
  );
}
