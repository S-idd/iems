package com.iems.dcg.validation;

import com.ideas.contracts.starter.ContractPayloadValidator;
import com.ideas.contracts.starter.ContractValidationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** Supplies the official validator with the exact mapper used by IEMS events. */
@Configuration
public class IemsContractValidatorConfig {
    @Bean
    public ContractPayloadValidator contractPayloadValidator(ContractValidationProperties properties) {
        return new ContractPayloadValidator(properties.getContractsRoot(), IemsEventJson.mapper());
    }
}
