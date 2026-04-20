'use client';

import React, { useState } from 'react';
import { Accordion, AccordionItem, Tag } from '@carbon/react';
import type { PlatformTsb } from '../../lib/api';
import styles from './PlatformTsbPanel.module.css';

interface PlatformTsbPanelProps {
    platformFamily: string;
    platformSiblings: string[];
    candidates: Array<{
        component: string;
        platform_tsbs: PlatformTsb[];
    }>;
}

function formatBulletinDate(raw: string): string {
    // Backend sends "YYYYMMDD" — convert to "YYYY-MM-DD"
    if (!raw || raw.length !== 8) return raw;
    return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
}

function TsbRow({ tsb }: { tsb: PlatformTsb }) {
    return (
        <div className={styles.tsbRow}>
            <div className={styles.tsbMeta}>
                <span className={styles.tsbBulletinNo}>{tsb.bulletin_no}</span>
                <span className={styles.tsbDate}>{formatBulletinDate(tsb.bulletin_date)}</span>
                <span className={styles.tsbVehicle}>
                    {tsb.make} {tsb.model}
                    {tsb.year ? ` (${tsb.year})` : ''}
                </span>
            </div>
            <p className={styles.tsbSummary}>{tsb.summary}</p>
        </div>
    );
}

export default function PlatformTsbPanel({
    platformFamily,
    platformSiblings,
    candidates,
}: PlatformTsbPanelProps) {
    const [expanded, setExpanded] = useState(false);

    // Collect all candidates that have platform TSBs
    const candidatesWithPlatformTsbs = candidates.filter(
        (c) => c.platform_tsbs && c.platform_tsbs.length > 0
    );

    const totalTsbCount = candidatesWithPlatformTsbs.reduce(
        (sum, c) => sum + c.platform_tsbs.length,
        0
    );

    if (totalTsbCount === 0) return null;

    return (
        <section
            className={styles.panel}
            aria-label={`Platform Family TSBs for ${platformFamily}`}
        >
            <div className={styles.header}>
                <div className={styles.titleRow}>
                    <span className={styles.label}>Platform Family TSBs</span>
                    <Tag type="blue" size="sm">
                        {platformFamily}
                    </Tag>
                    <Tag type="warm-gray" size="sm">
                        {totalTsbCount} bulletin{totalTsbCount !== 1 ? 's' : ''}
                    </Tag>
                </div>
                {platformSiblings.length > 0 && (
                    <p className={styles.siblingsNote}>
                        Also applies to: {platformSiblings.slice(0, 6).join(', ')}
                        {platformSiblings.length > 6 ? ` +${platformSiblings.length - 6} more` : ''}
                    </p>
                )}
            </div>

            <Accordion>
                {candidatesWithPlatformTsbs.map((candidate) => (
                    <AccordionItem
                        key={candidate.component}
                        title={
                            <span className={styles.accordionTitle}>
                                {candidate.component}
                                <Tag type="blue" size="sm" className={styles.countTag}>
                                    {candidate.platform_tsbs.length}
                                </Tag>
                            </span>
                        }
                    >
                        <div className={styles.tsbList}>
                            {candidate.platform_tsbs.map((tsb) => (
                                <TsbRow key={tsb.bulletin_no || tsb.nhtsa_id} tsb={tsb} />
                            ))}
                        </div>
                    </AccordionItem>
                ))}
            </Accordion>
        </section>
    );
}
